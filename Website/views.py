# =============================================================================
# 導入區域
# =============================================================================
# Django 相關導入
import uuid
from django.utils import timezone

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, connection
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect

from .models import UserProfile, Feedback, Coupon

# REST Framework 相關導入
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# 專案模型與序列化器導入
from .models import MenuItem, Order, OrderItem
from .serializers import MenuItemSerializer, CouponSerializer

# 其他標準庫導入
import json
import logging

# 設置日誌記錄
logger = logging.getLogger(__name__)


# =============================================================================
# 頁面渲染視圖
# =============================================================================

def page0(request):
    """登入/註冊頁面"""
    return render(request, 'page0_login.html')


# 登入處理視圖
def login_view(request):
    """
    處理用戶登入
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('page1')  # 修改此處，原本是 'home'
        else:
            return render(request, 'page0_login.html', {'error_message': '用戶名或密碼不正確'})  # 修改此處，原本是 'page0.html'
    return redirect('page0')


# 添加註冊處理視圖
def register_view(request):
    """
    處理用戶註冊
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone = request.POST.get('phone', '')

        # 驗證密碼
        if password != confirm_password:
            return render(request, 'page0_login.html', {'register_error': '兩次輸入的密碼不一致'})

        # 檢查用戶名是否已存在
        if User.objects.filter(username=username).exists():
            return render(request, 'page0_login.html', {'register_error': '用戶名已存在'})

        # 創建用戶
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user_profile = UserProfile.objects.create(user=user, phone=phone)

            # 自動登入
            login(request, user)
            return redirect('home')
        except Exception as e:
            return render(request, 'page0_login.html', {'register_error': f'註冊失敗: {str(e)}'})

    return redirect('page0')


# 添加登出處理視圖
def logout_view(request):
    """
    處理用戶登出
    """
    logout(request)
    return redirect('home')


def page1(request):
    """首頁"""
    return render(request, 'page1.html')


def page2_menu(request):
    """菜單頁面"""
    return render(request, 'page2_menu.html')


def page3_shopping_cart(request):
    """購物車頁面"""
    return render(request, 'page3_shopping-cart.html')


def page4_order_confirmation(request):
    """訂單確認頁面"""
    order_id = request.GET.get('order_id')
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'page4_order_confirmation.html', {'order': order})


def page5_order_status(request):
    """訂單狀態頁面"""
    return render(request, 'page5_order_status.html')


def admin_dashboard(request):
    """管理後台頁面"""
    return render(request, 'admin_dashboard.html')


# 添加檢查用戶認證狀態的API
@api_view(['GET'])
def check_auth(request):
    """
    檢查用戶是否已登入
    
    返回:
    - is_authenticated: 布爾值，表示用戶是否已登入
    - username: 如果已登入，返回用戶名
    """
    data = {
        'is_authenticated': request.user.is_authenticated,
    }
    if request.user.is_authenticated:
        data['username'] = request.user.username
    return Response(data)


# =============================================================================
# 購物車相關 API
# =============================================================================

@csrf_exempt
def save_cart(request):
    """
    儲存購物車內容至 session
    
    POST 請求參數:
    - items: 購物車項目列表
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        request.session['cart_items'] = data['items']
        return JsonResponse({'message': 'Cart saved successfully!'})


def get_cart(request):
    """
    從 session 獲取購物車內容
    
    返回:
    - items: 購物車項目列表
    """
    cart_items = request.session.get('cart_items', [])
    return JsonResponse({'items': cart_items})


# =============================================================================
# 訂單相關 API
# =============================================================================

@csrf_exempt
def submit_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_type = data.get('type')
            items = data.get('items', [])
            coupon_code = data.get('coupon_code', None)
            user = request.user if request.user.is_authenticated else None

            # 验证折扣券
            discount = 0
            coupon = None
            if coupon_code and user:
                try:
                    coupon = Coupon.objects.get(
                        code=coupon_code,
                        user=user,
                        is_used=False,
                        valid_until__gte=timezone.now()
                    )
                    discount = int(coupon.coupon_type)
                except Coupon.DoesNotExist:
                    return JsonResponse(
                        {'success': False, 'error': '无效的折扣券'},
                        status=400
                    )

            # 创建订单（强制关联用户，即使为None）
            order = Order.objects.create(
                user=user,  # 明确传递用户（可能是None）
                order_type=order_type,
                total_price=0  # 初始值
            )

            # 计算总价
            total_price = sum(
                MenuItem.objects.get(id=item['id']).price * item['count']
                for item in items
            )

            # 应用折扣
            final_price = max(0, total_price - discount)
            order.total_price = final_price
            order.save()

            # 创建订单项
            for item in items:
                menu_item = MenuItem.objects.get(id=item['id'])
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item['count'],
                    price=menu_item.price * item['count']
                )

            # 标记折扣券为已使用
            if coupon:
                coupon.is_used = True
                coupon.save()

            # 清空购物车
            request.session.pop('cart_items', None)

            return JsonResponse({
                'success': True,
                'order_id': str(order.order_id),
                'discount_applied': discount,
                'final_price': final_price
            })

        except Exception as e:
            logger.error(f"订单提交失败: {str(e)}", exc_info=True)
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=400
            )
    return JsonResponse(
        {'error': '仅支持POST请求'},
        status=405
    )


@csrf_exempt
@api_view(['GET'])
def get_orders(request):
    """
    獲取所有訂單列表
    
    返回:
    - 訂單列表，包含訂單詳情和項目
    """
    orders = Order.objects.all().order_by('-created_at')  # 按創建時間倒序排列
    data = [
        {
            'order_id': str(order.order_id),
            'sequence_number': order.sequence_number,
            'order_type': order.order_type,
            'gmail': order.gmail,
            'total_price': order.total_price,
            'created_at': order.created_at,
            'status': order.status,
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


@api_view(['GET', 'DELETE'])
def get_order_detail(request, order_id):
    """
    獲取或刪除單個訂單詳情
    
    GET 返回:
    - 單個訂單的詳細信息
    
    DELETE 返回:
    - 操作成功或失敗的消息
    """
    order = get_object_or_404(Order, order_id=order_id)

    if request.method == 'GET':
        data = {
            'order_id': str(order.order_id),
            'sequence_number': order.sequence_number,
            'order_type': order.order_type,
            'total_price': order.total_price,
            'created_at': order.created_at,
            'status': order.status,
            'items': [
                {
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'price': item.price
                }
                for item in order.items.all()
            ]
        }
        return Response(data)

    elif request.method == 'DELETE':
        order.delete()
        return Response({'success': True, 'message': '訂單已刪除'})


@api_view(['POST'])
def update_order_status(request, order_id):
    """
    更新訂單狀態
    
    POST 請求參數:
    - status: 新的訂單狀態 ('已送單', '製作中', '完成')
    
    返回:
    - 操作成功或失敗的消息
    """
    order = get_object_or_404(Order, order_id=order_id)
    status = request.data.get('status')
    if status in ['已送單', '製作中', '完成']:
        order.status = status
        order.save()
        return Response({'success': True, 'message': '訂單狀態已更新'})
    return Response({'success': False, 'message': '無效的狀態值'}, status=400)


# =============================================================================
# 菜單項目相關 API
# =============================================================================

@csrf_exempt
@api_view(['POST'])
def add_menu_item(request):
    """
    新增菜單項目
    
    POST 請求參數:
    - category: 分類
    - name: 名稱
    - price: 價格
    
    返回:
    - success: 成功或失敗
    - item_id: 新項目的 ID
    """
    data = request.data
    category = data.get('category')
    name = data.get('name')
    price = data.get('price')

    if not category or not name or not price:
        return Response({'success': False, 'message': '缺少必要參數'}, status=400)

    menu_item = MenuItem.objects.create(
        category=category,
        name=name,
        price=price
    )
    return Response({'success': True, 'message': '商品已新增', 'item_id': menu_item.id})


@api_view(['POST'])
def update_menu_item_status(request, item_id):
    """
    更新菜單項目狀態（例如標記為售完）
    
    POST 請求參數:
    - sold_out: 是否售完 (布爾值)
    
    返回:
    - 操作成功或失敗的消息
    """
    menu_item = get_object_or_404(MenuItem, id=item_id)
    sold_out = request.data.get('sold_out', False)
    menu_item.sold_out = sold_out
    menu_item.save()
    return Response({'success': True, 'message': '商品狀態已更新'})


class MenuItemListAPIView(generics.ListCreateAPIView):
    """
    菜單項目列表 API
    
    GET:
    獲取所有菜單項目
    
    POST:
    新增菜單項目
    """
    queryset = MenuItem.objects.all().order_by('id')  # 按 ID 排序
    serializer_class = MenuItemSerializer

    def perform_create(self, serializer):
        serializer.save()


class MenuItemDetailAPIView(generics.RetrieveDestroyAPIView):
    """
    菜單項目詳情 API
    
    GET:
    獲取單個菜單項目詳情
    
    DELETE:
    刪除菜單項目，並重新排列 ID
    """
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        """
        刪除菜單項目並重新排列 ID，保持 ID 連續性
        
        處理步驟:
        1. 刪除與該商品關聯的訂單項目
        2. 刪除商品本身
        3. 更新關聯表中的外鍵引用
        4. 重新排列後續商品的 ID
        """
        with transaction.atomic():
            # 獲取要刪除的實例
            instance = self.get_object()
            deleted_id = instance.id

            # 找出所有關聯的訂單項
            related_order_items = OrderItem.objects.filter(menu_item_id=deleted_id)

            # 處理關聯的訂單項
            if related_order_items.exists():
                related_order_items.delete()

            # 刪除商品
            self.perform_destroy(instance)

            # 獲取所有大於被刪除 ID 的商品
            items_to_update = MenuItem.objects.filter(id__gt=deleted_id).order_by('id')

            # 更新關聯表中的外鍵引用
            for item in items_to_update:
                OrderItem.objects.filter(menu_item_id=item.id).update(menu_item_id=item.id - 1)

            # 重新排列 ID
            for item in items_to_update:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Website_menuitem SET id = %s WHERE id = %s",
                        [item.id - 1, item.id]
                    )

        return Response({'success': True, 'message': '商品已刪除，ID 已重新排列'})


@api_view(['DELETE'])
def delete_order(request, order_id):
    """刪除單一訂單"""
    try:
        order = get_object_or_404(Order, order_id=order_id)
        with transaction.atomic():
            OrderItem.objects.filter(order=order).delete()
            order.delete()
        return Response({'success': True, 'message': '訂單刪除成功'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"刪除訂單時發生錯誤: {str(e)}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_completed_orders(request):
    """刪除所有已完成的訂單"""
    try:
        with transaction.atomic():
            completed_orders = Order.objects.filter(status='完成')
            order_ids = list(completed_orders.values_list('order_id', flat=True))
            OrderItem.objects.filter(order__order_id__in=order_ids).delete()
            count = completed_orders.count()
            completed_orders.delete()
        return Response({'success': True, 'message': f'成功刪除 {count} 筆已完成訂單'},
                        status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"刪除已完成訂單時發生錯誤: {str(e)}")
        return Response({'success': False, 'error': str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def is_superuser(user):
    """檢查是否為超級用戶"""
    return user.is_superuser


# 登入頁面（無需裝飾器，允許公開訪問）
def admin_dashboard_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    return render(request, 'admin_dashboard_login.html')


# 登入驗證
def admin_dashboard_auth(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            return render(request, 'admin_dashboard_login.html', {
                'error': '無效的憑證或您沒有管理員權限'
            })
    return redirect('admin_dashboard_login')


# 主控台頁面（受保護）
@login_required(login_url='/admin_dashboard/login/')
@user_passes_test(is_superuser)
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')


# 新增在 views.py
@api_view(['POST'])
def submit_feedback(request):
    """提交評價並進行抽獎"""
    if not request.user.is_authenticated:
        return Response({'error': '請先登入'}, status=401)

    order_id = request.data.get('order_id')
    rating = request.data.get('rating')

    try:
        order = Order.objects.get(order_id=order_id, status='完成')

        # 檢查是否已評價過
        if Feedback.objects.filter(order=order, user=request.user).exists():
            return Response({'error': '您已評價過此訂單'}, status=400)

        # 儲存評價
        feedback = Feedback.objects.create(
            user=request.user,
            order=order,
            rating=rating
        )

        # 抽獎邏輯
        import random
        lottery = random.choices(
            ['0', '10', '20', '30', '100'],
            weights=[40, 30, 20, 9, 1],
            k=1
        )[0]

        # 產生折價券
        coupon = Coupon.objects.create(
            user=request.user,
            coupon_type=lottery,
            code=f"COUPON-{uuid.uuid4().hex[:8].upper()}",
            valid_until=timezone.now() + timezone.timedelta(days=30)
        )

        return Response({
            'success': True,
            'coupon': CouponSerializer(coupon).data,
            'discount': int(lottery)
        })

    except Order.DoesNotExist:
        return Response({'error': '訂單不存在或尚未完成'}, status=404)


@api_view(['GET'])
def get_user_coupons(request):
    """獲取用戶可用折價券"""
    if not request.user.is_authenticated:
        return Response({'error': '請先登入'}, status=401)

    coupons = Coupon.objects.filter(
        user=request.user,
        is_used=False,
        valid_until__gte=timezone.now()
    )
    return Response(CouponSerializer(coupons, many=True).data)


@api_view(['GET'])
def get_menu_ratings(request):
    """獲取餐點平均評分"""
    from django.db.models import Avg
    ratings = MenuItem.objects.annotate(
        avg_rating=Avg('order__feedback__rating')
    ).values('id', 'name', 'avg_rating')
    return Response(ratings)


def page6_feedback(request):
    """反馈与优惠页面"""
    return render(request, 'page6_feedback-and-discount.html')
