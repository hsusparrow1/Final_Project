from django.db import models
import uuid  # 用來產生隨機不重複的訂單編號

#  菜單分類（餐點資料）
class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('三明治', '三明治'),
        ('吐司', '吐司'),
        ('貝果', '貝果'),
        ('可頌', '可頌'),
        ('沙拉', '沙拉'),
        ('飲品', '飲品'),
        ('甜品', '甜品'),
        ('套餐', '套餐'),
    ]

    id = models.AutoField(primary_key=True)  # 自動編號（1, 2, 3...）
    name = models.CharField(max_length=100)  # 餐點名稱
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)  # 類別
    description = models.TextField(blank=True)  # 餐點描述（可以留空）
    price = models.DecimalField(max_digits=6, decimal_places=2)  # 價格（例如 199.00）
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)  # 餐點圖片（可以留空）

    def __str__(self):
        return self.name

#  訂單（Order）
class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('內用', '內用'),
        ('外帶', '外帶'),
    ]

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # 隨機訂單編號
    order_type = models.CharField(max_length=5, choices=ORDER_TYPE_CHOICES)  # 內用/外帶
    gmail = models.EmailField(blank=True, null=True)  # 顧客 Gmail，可空白
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  # 訂單總價
    created_at = models.DateTimeField(auto_now_add=True)  # 建立時間（下單時間）

    class Meta:
        ordering = ['-created_at']  # 預設按照下單時間「新到舊」排列

    def __str__(self):
        return str(self.order_id)

    # 在 Order 模型添加
    def update_total(self):
        self.total_price = sum(item.price for item in self.items.all())
        self.save()

#  訂單細項（每筆餐點）
class OrderItem(models.Model):
    id = models.AutoField(primary_key=True)  # 自動流水號
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)  # 對應哪一張訂單
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)  # 對應哪個餐點
    quantity = models.PositiveIntegerField(default=1)  # 數量（不能負數）
    price = models.DecimalField(max_digits=8, decimal_places=2)  # 單項小計（單價×數量）

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.price = self.menu_item.price * self.quantity
        super().save(*args, **kwargs)


