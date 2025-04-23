// تهيئة التلميحات
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// تأكيد الحذف
function confirmDelete(event, message) {
    if (!confirm(message || 'هل أنت متأكد من الحذف؟')) {
        event.preventDefault();
        return false;
    }
    return true;
}

// تحديث الإجمالي في نموذج المبيعات
function updateTotal() {
    const quantity = parseFloat(document.getElementById('quantity').value) || 0;
    const price = parseFloat(document.getElementById('price').value) || 0;
    const totalElement = document.getElementById('total');
    if (totalElement) {
        const total = quantity * price;
        totalElement.value = total.toFixed(2);
    }
}

// البحث في الجداول
function searchTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    const filter = input.value.toLowerCase();
    const table = document.getElementById(tableId);
    const rows = table.getElementsByTagName('tr');

    for (let i = 1; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        let found = false;
        
        for (let j = 0; j < cells.length; j++) {
            const cell = cells[j];
            if (cell) {
                const text = cell.textContent || cell.innerText;
                if (text.toLowerCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }
        
        rows[i].style.display = found ? '' : 'none';
    }
}

// قراءة الباركود
function handleBarcodeScan(event) {
    if (event.keyCode === 13) { // Enter key
        const barcodeInput = document.getElementById('barcode');
        const barcode = barcodeInput.value.trim();
        
        if (barcode) {
            // إرسال طلب AJAX للبحث عن المنتج
            fetch(`/api/products/barcode/${barcode}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // تعبئة بيانات المنتج في النموذج
                        document.getElementById('product_id').value = data.product.id;
                        document.getElementById('product_name').value = data.product.name;
                        document.getElementById('price').value = data.product.price;
                        document.getElementById('quantity').focus();
                    } else {
                        alert('المنتج غير موجود!');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('حدث خطأ أثناء البحث عن المنتج');
                });
            
            barcodeInput.value = '';
        }
    }
}

// طباعة الفاتورة
function printInvoice(invoiceId) {
    window.open(`/invoice/print/${invoiceId}`, '_blank', 'width=800,height=600');
}

// تحديث حالة المخزون المنخفض
function checkLowStock() {
    fetch('/api/inventory/low-stock')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('low-stock-badge');
            if (badge) {
                badge.textContent = data.count;
                badge.style.display = data.count > 0 ? 'inline' : 'none';
            }
        })
        .catch(error => console.error('Error:', error));
}

// تحديث المخزون كل 5 دقائق
setInterval(checkLowStock, 300000); // 5 minutes

// تحرير الكتاب
function editBook(bookId) {
    fetch(`/api/books/${bookId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const book = data.book;
                document.getElementById('barcode').value = book.barcode;
                document.getElementById('title').value = book.title;
                document.getElementById('author').value = book.author;
                document.getElementById('publisher').value = book.publisher;
                document.getElementById('price').value = book.price;
                document.getElementById('quantity').value = book.quantity;
                document.getElementById('category').value = book.category;
                
                const addBookForm = document.getElementById('addBookForm');
                addBookForm.action = `/api/books/${bookId}/update`;
                
                const modal = new bootstrap.Modal(document.getElementById('addBookModal'));
                modal.show();
            } else {
                alert('حدث خطأ في تحميل بيانات الكتاب');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('حدث خطأ في تحميل بيانات الكتاب');
        });
}