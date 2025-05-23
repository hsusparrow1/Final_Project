
# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from .models import MenuItem, Order, OrderItem  # 把你的 model 匯入

# 菜單餐點
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'sold_out', 'member_only')  # 加入 member_only
    list_filter = ('category', 'sold_out', 'member_only')  # 增加 member_only 篩選
    search_fields = ('name',)
    readonly_fields = ('image_tag',)

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '''
                <div style="width: 100px; height: 100px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd;" >'
                '<img src="{}" style="max-width: 100%; max-height: 100%; object-fit: cover;" />'
                <div>
                ''',
                 obj.image.url)
        return "-"
    image_tag.short_description = '圖片預覽'

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

