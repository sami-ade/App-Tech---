from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin_user():
    with app.app_context():
        # تحقق مما إذا كان المستخدم المسؤول موجود بالفعل
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                is_active=True,
                full_name='مدير النظام',
                email='admin@example.com'
            )
            db.session.add(admin)
            db.session.commit()
            print('تم إنشاء المستخدم المسؤول بنجاح')
        else:
            print('المستخدم المسؤول موجود بالفعل')

if __name__ == '__main__':
    create_admin_user()