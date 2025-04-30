from django.shortcuts import render, get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
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

def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

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

@csrf_exempt
@api_view(['GET'])
def get_orders(request):
    """取得所有訂單"""
    orders = Order.objects.all()
    data = [
        {
            'order_id': str(order.order_id),
            'sequence_number': order.sequence_number,  # 新增流水號
            'order_type': order.order_type,
            'gmail': order.gmail,
            'total_price': order.total_price,
            'created_at': order.created_at,
            'status': order.status,  # 確保返回 status
            'items': [
                {
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'price': item.price
                }
                for item in order.items.all()
            ]
        }
        for order in orders
    ]
    return Response(data)

@api_view(['POST'])
def update_order_status(request, order_id):
    """更新訂單狀態"""
    order = get_object_or_404(Order, order_id=order_id)
    status = request.data.get('status')
    if status in ['已送單', '製作中', '完成']:
        order.status = status
        order.save()
        return Response({'success': True, 'message': '訂單狀態已更新'})
    return Response({'success': False, 'message': '無效的狀態值'}, status=400)

@api_view(['POST'])
def update_menu_item_status(request, item_id):
    """更新商品狀態（例如已售完）"""
    menu_item = get_object_or_404(MenuItem, id=item_id)
    sold_out = request.data.get('sold_out', False)
    menu_item.sold_out = sold_out
    menu_item.save()
    return Response({'success': True, 'message': '商品狀態已更新'})

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

def page4_order_confirmation(request):
    order_id = request.GET.get('order_id')  # 從 URL 參數中獲取訂單 ID
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'page4_order_confirmation.html', {'order': order})

