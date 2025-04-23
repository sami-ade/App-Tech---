from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import func, text
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

# إنشاء تطبيق Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إنشاء قاعدة البيانات
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# نماذج قاعدة البيانات
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    
    # معلومات المستخدم
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # صلاحيات المستخدم
    can_manage_inventory = db.Column(db.Boolean, default=False)
    can_manage_sales = db.Column(db.Boolean, default=False)
    can_manage_purchases = db.Column(db.Boolean, default=False)
    can_manage_customers = db.Column(db.Boolean, default=False)
    can_manage_suppliers = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=False)
    
    # العلاقات
    invoices_created = db.relationship('Invoice', backref='creator', lazy=True,
                                     foreign_keys='Invoice.created_by')
    transactions_created = db.relationship('Transaction', backref='creator', lazy=True,
                                         foreign_keys='Transaction.created_by')

    def is_admin(self):
        return self.role == 'admin'

    def has_permission(self, permission):
        if self.is_admin():
            return True
        return getattr(self, f'can_{permission}', False)

    @property
    def permissions(self):
        perms = {
            'manage_inventory': self.can_manage_inventory,
            'manage_sales': self.can_manage_sales,
            'manage_purchases': self.can_manage_purchases,
            'manage_customers': self.can_manage_customers,
            'manage_suppliers': self.can_manage_suppliers,
            'manage_users': self.can_manage_users,
            'view_reports': self.can_view_reports
        }
        if self.is_admin():
            return {k: True for k in perms.keys()}
        return perms

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category_rel', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    subcategory = db.Column(db.String(50))  # للتصنيفات الفرعية
    price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    min_quantity = db.Column(db.Integer, default=10)
    barcode = db.Column(db.String(50), unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))  # المورد الرئيسي
    reorder_point = db.Column(db.Integer, default=5)  # نقطة إعادة الطلب
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # إحصائيات المنتج
    total_sales = db.Column(db.Integer, default=0)  # إجمالي المبيعات
    last_sale_date = db.Column(db.DateTime)  # تاريخ آخر عملية بيع
    last_purchase_date = db.Column(db.DateTime)  # تاريخ آخر عملية شراء
    average_daily_sales = db.Column(db.Float, default=0)  # متوسط المبيعات اليومية

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    total_amount = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    total = db.Column(db.Float, nullable=False)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    invoice_number = db.Column(db.String(50))
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    items = db.relationship('PurchaseItem', backref='purchase', lazy=True)

class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    balance = db.Column(db.Float, default=0.0)
    credit_limit = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    tax_number = db.Column(db.String(50))
    purchases = db.relationship('Purchase', backref='supplier', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(20), nullable=False)  # payment, receipt, expense, salary
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20))
    reference_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    category = db.Column(db.String(50))  # تصنيف المصروف/الإيراد
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class DailyReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    total_sales = db.Column(db.Float, default=0)
    total_purchases = db.Column(db.Float, default=0)
    total_expenses = db.Column(db.Float, default=0)
    total_receipts = db.Column(db.Float, default=0)
    cash_balance = db.Column(db.Float, default=0)
    profit = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BackupLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    size = db.Column(db.Integer)  # حجم الملف بالبايت
    status = db.Column(db.String(20))  # success, failed
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# الصفحة الرئيسية
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('خطأ في اسم المستخدم أو كلمة المرور')
    return render_template('login.html')

# تسجيل الخروج
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# صفحة المخزون
@app.route('/inventory')
@login_required
def inventory():
    if not current_user.has_permission('manage_inventory'):
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect(url_for('index'))
    products = Product.query.all()
    return render_template('inventory.html', products=products)

# إضافة منتج جديد
@app.route('/api/products/add', methods=['POST'])
@login_required
def add_product():
    if not current_user.has_permission('manage_inventory'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لإضافة منتجات'})
    
    try:
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            category=request.form['category'],
            price=float(request.form['price']),
            cost_price=float(request.form['cost_price']),
            quantity=int(request.form['quantity']),
            min_quantity=int(request.form['min_quantity']),
            barcode=request.form['barcode']
        )
        db.session.add(product)
        db.session.commit()
        flash('تم إضافة المنتج بنجاح')
        return redirect(url_for('inventory'))
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء إضافة المنتج')
        return redirect(url_for('inventory'))

# الحصول على بيانات منتج
@app.route('/api/products/<int:product_id>')
@login_required
def get_product(product_id):
    if not current_user.has_permission('manage_inventory'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية للوصول إلى بيانات المنتجات'})
    
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'success': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'category': product.category,
            'price': product.price,
            'cost_price': product.cost_price,
            'quantity': product.quantity,
            'min_quantity': product.min_quantity,
            'barcode': product.barcode
        }
    })

# تحديث بيانات منتج
@app.route('/api/products/<int:product_id>/update', methods=['POST'])
@login_required
def update_product(product_id):
    if not current_user.has_permission('manage_inventory'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لتعديل المنتجات'})
    
    product = Product.query.get_or_404(product_id)
    try:
        product.name = request.form['name']
        product.description = request.form['description']
        product.category = request.form['category']
        product.price = float(request.form['price'])
        product.cost_price = float(request.form['cost_price'])
        product.quantity = int(request.form['quantity'])
        product.min_quantity = int(request.form['min_quantity'])
        product.barcode = request.form['barcode']
        db.session.commit()
        flash('تم تحديث بيانات المنتج بنجاح')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تحديث بيانات المنتج')
    return redirect(url_for('inventory'))

# حذف منتج
@app.route('/api/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.has_permission('manage_inventory'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لحذف المنتجات'})
    
    product = Product.query.get_or_404(product_id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('تم حذف المنتج بنجاح')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء حذف المنتج')
    return redirect(url_for('inventory'))

# المنتجات منخفضة المخزون
@app.route('/api/inventory/low-stock')
@login_required
def get_low_stock_alert():
    if not current_user.has_permission('manage_inventory'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية للوصول إلى بيانات المخزون'})
    
    low_stock_products = Product.query.filter(Product.quantity <= Product.min_quantity).all()
    return jsonify({
        'success': True,
        'count': len(low_stock_products),
        'products': [{
            'id': p.id,
            'name': p.name,
            'quantity': p.quantity,
            'min_quantity': p.min_quantity,
            'category': p.category_rel.name if p.category_rel else None,
            'supplier': p.supplier.name if p.supplier else None
        } for p in low_stock_products]
    })

# صفحة المبيعات
@app.route('/sales')
@login_required
def sales():
    if not current_user.has_permission('manage_sales'):
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect(url_for('index'))
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    return render_template('sales.html', invoices=invoices)

# إنشاء فاتورة جديدة
@app.route('/api/sales/create', methods=['POST'])
@login_required
def create_sale():
    if not current_user.has_permission('manage_sales'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لإنشاء فاتورة'})
    
    try:
        # إنشاء رقم فاتورة جديد
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{(last_invoice.id + 1 if last_invoice else 1):04d}"
        
        # إنشاء الفاتورة
        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=request.form.get('customer_id'),
            total_amount=float(request.form.get('total_amount', 0)),
            discount=float(request.form.get('discount', 0)),
            paid_amount=float(request.form.get('paid_amount', 0)),
            payment_method=request.form.get('payment_method'),
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        db.session.add(invoice)
        
        # إضافة منتجات الفاتورة
        items = request.json.get('items', [])
        for item in items:
            invoice_item = InvoiceItem(
                invoice=invoice,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price'],
                discount=item.get('discount', 0),
                total=item['total']
            )
            db.session.add(invoice_item)
            
            # تحديث المخزون
            product = Product.query.get(item['product_id'])
            if product:
                product.quantity -= item['quantity']
        
        # إضافة معاملة مالية
        if invoice.paid_amount > 0:
            transaction = Transaction(
                type='payment',
                amount=invoice.paid_amount,
                payment_method=invoice.payment_method,
                customer_id=invoice.customer_id,
                invoice_id=invoice.id,
                created_by=current_user.id,
                notes=f"دفعة فاتورة رقم {invoice.invoice_number}"
            )
            db.session.add(transaction)
        
        db.session.commit()
        return jsonify({'success': True, 'invoice_id': invoice.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء إنشاء الفاتورة'})

# طباعة فاتورة
@app.route('/api/sales/<int:invoice_id>/print')
@login_required
def print_invoice(invoice_id):
    if not current_user.has_permission('manage_sales'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لطباعة الفاتورة'})
    
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('invoice_print.html', invoice=invoice)

# طباعة الباركود
@app.route('/api/products/<int:product_id>/barcode/print')
@login_required
def print_barcode(product_id):
    if not current_user.has_permission('manage_inventory'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لطباعة الباركود'})
    
    product = Product.query.get_or_404(product_id)
    try:
        # إنشاء رمز الباركود باستخدام المكتبة python-barcode
        import barcode
        from barcode.writer import ImageWriter
        from io import BytesIO
        
        # إنشاء الباركود
        ean = barcode.get('ean13', product.barcode, writer=ImageWriter())
        buffer = BytesIO()
        ean.write(buffer)
        
        # إرجاع صورة الباركود
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'barcode_{product.barcode}.png'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء إنشاء الباركود'})

# إدارة المستخدمين
@app.route('/users')
@login_required
def users():
    if not current_user.has_permission('manage_users'):
        flash('ليس لديك صلاحية للوصول إلى هذه الصفحة')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('users.html', users=users)

# إضافة مستخدم جديد
@app.route('/api/users/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.has_permission('manage_users'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لإضافة مستخدمين'})
    
    try:
        user = User(
            username=request.form['username'],
            password_hash=generate_password_hash(request.form['password']),
            full_name=request.form['full_name'],
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            role=request.form['role']
        )
        
        if user.role != 'admin':
            user.can_manage_inventory = bool(request.form.get('can_manage_inventory'))
            user.can_manage_sales = bool(request.form.get('can_manage_sales'))
            user.can_manage_purchases = bool(request.form.get('can_manage_purchases'))
            user.can_manage_customers = bool(request.form.get('can_manage_customers'))
            user.can_manage_suppliers = bool(request.form.get('can_manage_suppliers'))
            user.can_manage_users = bool(request.form.get('can_manage_users'))
            user.can_view_reports = bool(request.form.get('can_view_reports'))
        
        db.session.add(user)
        db.session.commit()
        flash('تم إضافة المستخدم بنجاح')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء إضافة المستخدم')
    return redirect(url_for('users'))

# الحصول على بيانات مستخدم
@app.route('/api/users/<int:user_id>')
@login_required
def get_user(user_id):
    if not current_user.has_permission('manage_users'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية للوصول إلى بيانات المستخدمين'})
    
    user = User.query.get_or_404(user_id)
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'phone': user.phone,
            'role': user.role,
            'permissions': user.permissions
        }
    })

# تحديث بيانات مستخدم
@app.route('/api/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    if not current_user.has_permission('manage_users'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لتعديل المستخدمين'})
    
    user = User.query.get_or_404(user_id)
    try:
        user.full_name = request.form.get('full_name', user.full_name)
        user.email = request.form.get('email', user.email)
        user.phone = request.form.get('phone', user.phone)
        db.session.commit()
        flash('تم تحديث بيانات المستخدم بنجاح')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تحديث بيانات المستخدم')
    return redirect(url_for('users'))

# التقارير المالية والإحصائية

@app.route('/api/reports/daily', methods=['GET'])
@login_required
def get_daily_report():
    if not current_user.has_permission('view_reports'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لعرض التقارير'})
    
    date = request.args.get('date', datetime.now().date().isoformat())
    report = DailyReport.query.filter_by(date=date).first()
    
    if not report:
        # إنشاء تقرير جديد
        sales = db.session.query(func.sum(Invoice.total_amount)).filter(
            func.date(Invoice.date) == date
        ).scalar() or 0
        
        purchases = db.session.query(func.sum(Purchase.total_amount)).filter(
            func.date(Purchase.date) == date
        ).scalar() or 0
        
        expenses = db.session.query(func.sum(Transaction.amount)).filter(
            func.date(Transaction.date) == date,
            Transaction.type == 'expense'
        ).scalar() or 0
        
        receipts = db.session.query(func.sum(Transaction.amount)).filter(
            func.date(Transaction.date) == date,
            Transaction.type == 'receipt'
        ).scalar() or 0
        
        report = DailyReport(
            date=date,
            total_sales=sales,
            total_purchases=purchases,
            total_expenses=expenses,
            total_receipts=receipts,
            cash_balance=receipts - expenses,
            profit=sales - purchases - expenses,
            created_by=current_user.id
        )
        db.session.add(report)
        db.session.commit()
    
    return jsonify({
        'success': True,
        'report': {
            'date': report.date.isoformat(),
            'total_sales': report.total_sales,
            'total_purchases': report.total_purchases,
            'total_expenses': report.total_expenses,
            'total_receipts': report.total_receipts,
            'cash_balance': report.cash_balance,
            'profit': report.profit,
            'notes': report.notes
        }
    })

@app.route('/api/reports/inventory/low-stock')
@login_required
def get_low_stock_report():
    if not current_user.has_permission('view_reports'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لعرض التقارير'})
    
    products = Product.query.filter(
        Product.quantity <= Product.reorder_point
    ).all()
    
    return jsonify({
        'success': True,
        'products': [{
            'id': p.id,
            'name': p.name,
            'category': p.category_rel.name,
            'quantity': p.quantity,
            'reorder_point': p.reorder_point,
            'supplier': p.supplier.name if p.supplier else None
        } for p in products]
    })

@app.route('/api/reports/sales/top-products')
@login_required
def get_top_products():
    if not current_user.has_permission('view_reports'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لعرض التقارير'})
    
    period = request.args.get('period', 'month')  # day, week, month, year
    limit = int(request.args.get('limit', 10))
    
    if period == 'month':
        date_filter = func.date(Invoice.date) >= func.date_sub(func.now(), text('INTERVAL 1 MONTH'))
    elif period == 'week':
        date_filter = func.date(Invoice.date) >= func.date_sub(func.now(), text('INTERVAL 1 WEEK'))
    elif period == 'year':
        date_filter = func.date(Invoice.date) >= func.date_sub(func.now(), text('INTERVAL 1 YEAR'))
    else:  # day
        date_filter = func.date(Invoice.date) == func.current_date()
    
    top_products = db.session.query(
        Product.id,
        Product.name,
        func.sum(InvoiceItem.quantity).label('total_quantity'),
        func.sum(InvoiceItem.total).label('total_amount')
    ).join(InvoiceItem).join(Invoice).filter(
        date_filter
    ).group_by(
        Product.id
    ).order_by(
        text('total_quantity DESC')
    ).limit(limit).all()
    
    return jsonify({
        'success': True,
        'period': period,
        'products': [{
            'id': p.id,
            'name': p.name,
            'total_quantity': int(p.total_quantity),
            'total_amount': float(p.total_amount)
        } for p in top_products]
    })



# النسخ الاحتياطي

@app.route('/api/backup/create', methods=['POST'])
@login_required
def create_backup():
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لإنشاء نسخة احتياطية'})
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # نسخ قاعدة البيانات
        db_file = os.path.join(app.root_path, 'library.db')
        backup_file = os.path.join(backup_dir, f'library_{timestamp}.db')
        import shutil
        shutil.copy2(db_file, backup_file)
        
        # تسجيل عملية النسخ
        log = BackupLog(
            date=datetime.now(),
            file_path=backup_file,
            size=os.path.getsize(backup_file),
            status='success',
            created_by=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء نسخة احتياطية بنجاح',
            'backup_file': backup_file
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}'
        })

@app.route('/api/backup/list')
@login_required
def list_backups():
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لعرض النسخ الاحتياطية'})
    
    logs = BackupLog.query.order_by(BackupLog.date.desc()).all()
    return jsonify({
        'success': True,
        'backups': [{
            'id': log.id,
            'date': log.date.isoformat(),
            'file_path': log.file_path,
            'size': log.size,
            'status': log.status
        } for log in logs]
    })

@app.route('/api/backup/restore/<int:backup_id>', methods=['POST'])
@login_required
def restore_backup(backup_id):
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لاستعادة النسخ الاحتياطية'})
    
    backup = BackupLog.query.get_or_404(backup_id)
    
    try:
        if not os.path.exists(backup.file_path):
            return jsonify({
                'success': False,
                'message': 'ملف النسخة الاحتياطية غير موجود'
            })
        
        # إيقاف التطبيق مؤقتاً
        # TODO: implement proper application shutdown
        
        # استعادة قاعدة البيانات
        db_file = os.path.join(app.root_path, 'library.db')
        import shutil
        shutil.copy2(backup.file_path, db_file)
        
        return jsonify({
            'success': True,
            'message': 'تم استعادة النسخة الاحتياطية بنجاح. يرجى إعادة تشغيل التطبيق.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'حدث خطأ أثناء استعادة النسخة الاحتياطية: {str(e)}'
        })

# تغيير حالة المستخدم (تفعيل/تعطيل)
@app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if not current_user.has_permission('manage_users'):
        return jsonify({'success': False, 'message': 'ليس لديك صلاحية لتعديل المستخدمين'})
    
    if user_id == current_user.id:
        flash('لا يمكنك تغيير حالة حسابك الشخصي')
        return redirect(url_for('users'))
    
    user = User.query.get_or_404(user_id)
    try:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'تفعيل' if user.is_active else 'تعطيل'
        flash(f'تم {status} المستخدم بنجاح')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تحديث حالة المستخدم')
    return redirect(url_for('users'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)