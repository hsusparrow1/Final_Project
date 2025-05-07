
# Register your models here.
from django.contrib import admin
from .models import MenuItem, Order, OrderItem  # 把你的 model 匯入

# 菜單餐點
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price')  # 後台列表會顯示這幾個欄位
    list_filter = ('category',)  # 右邊可以用分類快速篩選
    search_fields = ('name',)    # 上面有搜尋功能（搜尋餐點名字）

# 訂單
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'order_type', 'gmail', 'total_price', 'created_at')
    list_filter = ('order_type',)
    search_fields = ('gmail', 'order_id')

# 訂單細項
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'price')
    search_fields = ('menu_item__name',)

