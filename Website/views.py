from django.shortcuts import render
from rest_framework import generics
from .models import MenuItem, Order, OrderItem
from .serializers import MenuItemSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# 你原本的頁面視圖 (保持不變)
def page1(request):
    return render(request, 'page1.html')

def page2_menu(request):
    return render(request, 'page2_menu.html')  # 渲染 page2_menu.html 頁面

def page3_shopping_cart(request):
    return render(request, 'page3_shopping-cart.html')  # 渲染 page3_shopping-cart.html 頁面

@csrf_exempt
def save_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        request.session['cart_items'] = data['items']
        return JsonResponse({'message': 'Cart saved successfully!'})


@csrf_exempt
def submit_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_type = data.get('type')
            items = data.get('items', [])

            # 創建新訂單
            order = Order.objects.create(
                order_type=order_type,
                gmail='',  # 您可以根據需要添加郵件收集功能
                total_price=0  # 初始值，後面會計算
            )

            total_price = 0
            for item_data in items:
                menu_item = MenuItem.objects.get(id=item_data['id'])
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item_data['count'],
                    price=menu_item.price * item_data['count']
                )
                total_price += order_item.price

            # 更新訂單總價
            order.total_price = total_price
            order.save()

            # 清空購物車
            if 'cart_items' in request.session:
                del request.session['cart_items']

            return JsonResponse({'success': True, 'order_id': str(order.order_id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)
def get_cart(request):
    cart_items = request.session.get('cart_items', [])
    return JsonResponse({'items': cart_items})

# 新增的 API 視圖
class MenuItemListAPIView(generics.ListAPIView):
    """
    獲取所有商品列表的 API
    範例請求: GET /api/menu/
    """
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

class MenuItemDetailAPIView(generics.RetrieveAPIView):
    """
    獲取單個商品詳情的 API
    範例請求: GET /api/menu/1/  (1 是商品 ID)
    """
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    lookup_field = 'id'

