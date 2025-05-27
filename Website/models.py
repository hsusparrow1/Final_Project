from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
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
        ('會員', '會員')
    ]

    id = models.AutoField(primary_key=True)  # 自動編號（1, 2, 3...）
    name = models.CharField(max_length=100)  # 餐點名稱
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)  # 類別
    description = models.TextField(blank=True)  # 餐點描述（可以留空）
    price = models.DecimalField(max_digits=6, decimal_places=2)  # 價格（例如 199.00）
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)  # 餐點圖片（可以留空）
    sold_out = models.BooleanField(default=False)  # 新增欄位：是否已售完
    member_only = models.BooleanField(default=False)  # 是否僅限會員購買

    def __str__(self):
        return self.name


#  訂單（Order）
class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('內用', '內用'),
        ('外帶', '外帶'),
    ]

    STATUS_CHOICES = [
        ('已送單', '已送單'),
        ('製作中', '製作中'),
        ('完成', '完成'),
    ]
    
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # 隨機訂單編號
    sequence_number = models.PositiveIntegerField(default=0, editable=False)  # 流水號
    order_type = models.CharField(max_length=5, choices=ORDER_TYPE_CHOICES)  # 內用/外帶
    gmail = models.EmailField(blank=True, null=True)  # 顧客 Gmail，可空白
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  # 訂單總價
    created_at = models.DateTimeField(auto_now_add=True)  # 建立時間（下單時間）
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='已送單')  # 訂單狀態
    coupon = models.ForeignKey('Coupon', null=True, blank=True, on_delete=models.SET_NULL)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    class Meta:
        ordering = ['created_at']  # 按照下單時間「舊到新」排列

    def save(self, *args, **kwargs):
        if not self.sequence_number:  # 如果流水號尚未生成
            last_order = Order.objects.order_by('-sequence_number').first()
            self.sequence_number = (last_order.sequence_number + 1) if last_order else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"訂單 {self.sequence_number}"

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


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])  # 1-5星
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'order')  # 防止重複評價


class Coupon(models.Model):
    COUPON_TYPES = [
        ('10', '折10元'),
        ('20', '折20元'),
        ('30', '折30元'),
        ('100', '免單'),
        ('0', '銘謝惠顧')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon_type = models.CharField(max_length=3, choices=COUPON_TYPES)
    code = models.CharField(max_length=20, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()

    def __str__(self):
        return f"{self.get_coupon_type_display()} (到期: {self.valid_until.strftime('%Y-%m-%d')})"