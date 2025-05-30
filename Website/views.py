# =============================================================================
# 導入區域
# =============================================================================
# Django 相關導入
import uuid
from django.utils import timezone

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, connection
from django.db.models import Avg, Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

# 專案模型與序列化器導入
from .models import UserProfile, Feedback, Coupon, MenuItem, Order, OrderItem, MenuRating
from .serializers import MenuItemSerializer, CouponSerializer

# REST Framework 相關導入
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

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


def login_view(request):
    """處理用戶登入"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', None) # 從 POST 獲取 next (如果表單有) 或從 GET
        if not next_url:
            next_url = request.GET.get('next', None)


        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if next_url: # 如果有 next 參數，跳轉到該 URL
                return redirect(next_url)
            return redirect('page1') # 預設跳轉到 page1
        else:
            return render(request, 'page0_login.html', {'error_message': '用戶名或密碼不正確', 'next': next_url})
    
    # 如果是 GET 請求，也傳遞 next 參數給模板
    next_url_get = request.GET.get('next', '')
    return render(request, 'page0_login.html', {'next': next_url_get}) # 修改這裡，確保 GET 請求也能渲染登入頁


def register_view(request):
    """處理用戶註冊"""
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


def logout_view(request):
    """處理用戶登出"""
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


def page6_feedback(request):
    """評價與優惠頁面"""
    return render(request, 'page6_feedback-and-discount.html')


def admin_dashboard(request):
    """管理後台頁面"""
    return render(request, 'admin_dashboard.html')


# =============================================================================
# 認證與權限相關 API
# =============================================================================

@api_view(['GET'])
def check_auth(request):
    """檢查用戶是否已登入"""
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
    """儲存購物車內容至 session"""
    if request.method == 'POST':
        data = json.loads(request.body)
        request.session['cart_items'] = data['items']
        return JsonResponse({'message': '購物車已儲存成功！'})

def get_cart(request):
    """從 session 獲取購物車內容"""
    cart_items = request.session.get('cart_items', [])
    return JsonResponse({'items': cart_items})


# =============================================================================
# 訂單相關 API
# =============================================================================

@csrf_exempt
def submit_order(request):
    """提交訂單"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_type = data.get('type')
            items = data.get('items', [])
            coupon_code = data.get('coupon_code', None)
            user = request.user if request.user.is_authenticated else None

            # 驗證折價券
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
                        {'success': False, 'error': '無效的折價券'},
                        status=400
                    )

            # 先計算總價
            total_price = sum(
                MenuItem.objects.get(id=item['id']).price * item['count']
                for item in items
            )

            # 應用折扣
            final_price = max(0, total_price - discount)

            # 創建訂單（使用已計算好的 final_price）
            order = Order.objects.create(
                user=user,
                order_type=order_type,
                total_price=final_price,
                coupon=coupon  # 確保這行存在
            )

            # 創建訂單項目
            for item in items:
                menu_item = MenuItem.objects.get(id=item['id'])
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item['count'],
                    price=menu_item.price * item['count']
                )

            # 標記折價券為已使用
            if coupon:
                coupon.is_used = True
                coupon.save()

            # 清空購物車
            request.session.pop('cart_items', None)

            return JsonResponse({
                'success': True,
                'order_id': str(order.order_id),
                'discount_applied': discount,
                'final_price': final_price
            })

        except Exception as e:
            logger.error(f"訂單提交失敗: {str(e)}", exc_info=True)
            return JsonResponse(
                {'success': False, 'error': str(e)},
                status=400
            )
    return JsonResponse(
        {'error': '僅支援POST請求'},
        status=405
    )


@csrf_exempt
@api_view(['GET'])
def get_orders(request):
    """獲取所有訂單列表"""
    orders = Order.objects.all().order_by('-created_at')
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
    """獲取或刪除單個訂單詳情"""
    order = get_object_or_404(Order, order_id=order_id)

    if request.method == 'GET':
        has_participated = False
        # 只有在用戶已登入的情況下才檢查是否已參與抽獎
        if request.user.is_authenticated:
            has_participated = Feedback.objects.filter(order=order, user=request.user).exists()
        
        data = {
            'order_id': str(order.order_id),
            'sequence_number': order.sequence_number,
            'order_type': order.order_type,
            'total_price': order.total_price,
            'created_at': order.created_at,
            'status': order.status,
            'coupon_type': getattr(getattr(order, 'coupon', None), 'coupon_type', None),
            'coupon_code': getattr(getattr(order, 'coupon', None), 'code', None),
            'has_participated_in_draw': has_participated, # 新增此欄位
            'items': [
                {
                    'menu_item_id': item.menu_item.id, 
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
    """更新訂單狀態"""
    order = get_object_or_404(Order, order_id=order_id)
    status_value = request.data.get('status')
    if status_value in ['已送單', '製作中', '完成']:
        order.status = status_value
        order.save()
        return Response({'success': True, 'message': '訂單狀態已更新'})
    return Response({'success': False, 'message': '無效的狀態值'}, status=400)


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


# =============================================================================
# 菜單項目相關 API
# =============================================================================

@csrf_exempt
@api_view(['POST'])
def add_menu_item(request):
    """新增菜單項目"""
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
    """更新菜單項目狀態（例如標記為售完）"""
    menu_item = get_object_or_404(MenuItem, id=item_id)
    sold_out = request.data.get('sold_out', False)
    menu_item.sold_out = sold_out
    menu_item.save()
    return Response({'success': True, 'message': '商品狀態已更新'})


class MenuItemListAPIView(generics.ListCreateAPIView):
    """菜單項目列表 API"""
    queryset = MenuItem.objects.all().order_by('id')
    serializer_class = MenuItemSerializer

    def perform_create(self, serializer):
        serializer.save()


class MenuItemDetailAPIView(generics.RetrieveDestroyAPIView):
    """菜單項目詳情 API"""
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        """刪除菜單項目並重新排列 ID，保持 ID 連續性"""
        with transaction.atomic():
            instance = self.get_object()
            deleted_id = instance.id

            # 刪除關聯的訂單項目
            related_order_items = OrderItem.objects.filter(menu_item_id=deleted_id)
            if related_order_items.exists():
                related_order_items.delete()

            # 刪除商品
            self.perform_destroy(instance)

            # 取得所有大於被刪除 ID 的商品
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


# =============================================================================
# 管理後台相關視圖
# =============================================================================

def is_superuser(user):
    """檢查是否為超級用戶"""
    return user.is_superuser


def admin_dashboard_login(request):
    """管理後台登入頁面（允許公開訪問）"""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')
    return render(request, 'admin_dashboard_login.html')


def admin_dashboard_auth(request):
    """管理後台登入驗證"""
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


@login_required(login_url='/admin_dashboard/login/')
@user_passes_test(is_superuser)
def admin_dashboard(request):
    """管理後台主控台頁面（需超級用戶）"""
    return render(request, 'admin_dashboard.html')


# =============================================================================
# 評價與折價券相關 API
# =============================================================================

@api_view(['POST'])
def submit_feedback(request):
    """提交評價並進行抽獎"""
    if not request.user.is_authenticated:
        return Response({'error': '請先登入'}, status=401)

    order_id = request.data.get('order_id')
    discount = request.data.get('discount', 0)

    try:
        # 嘗試找到訂單，訂單必須是 '完成' 狀態
        # 它可以屬於當前登入的用戶，或者是一個匿名訂單
        possible_orders_query = Order.objects.filter(order_id=order_id, status='完成')
        
        order = possible_orders_query.filter(user=request.user).first()
        
        if not order:
            # 如果找不到屬於當前用戶的訂單，則檢查是否為匿名訂單
            order = possible_orders_query.filter(user__isnull=True).first()
        
        if not order:
            # 如果仍然找不到訂單，則表示訂單不存在或不符合條件
            raise Order.DoesNotExist

        # 檢查此用戶是否已對此訂單提交過回饋 (參與過抽獎)
        if Feedback.objects.filter(order=order, user=request.user).exists():
            # 此處可以根據您的業務邏輯決定是否允許重複抽獎或提示已參與
            # 目前的程式碼是 pass，即允許繼續執行 (可能導致重複創建 Feedback 或 Coupon)
            # 如果不允許重複，應返回錯誤：
            # return Response({'error': '您已參與過此訂單的抽獎活動'}, status=status.HTTP_400_BAD_REQUEST)
            pass # 暫時允許，但您可能需要更精確的邏輯來防止重複抽獎

        Feedback.objects.update_or_create(
            user=request.user,
            order=order,
            defaults={
                # 'rating': rating, # 如果 rating 字段允許 null 或有預設值
            }
        )

        if discount > 0:
            coupon = Coupon.objects.create(
                user=request.user,
                coupon_type=str(discount),
                code=f"COUPON-{uuid.uuid4().hex[:8].upper()}",
                valid_until=timezone.now() + timezone.timedelta(days=30)
            )
            return Response({
                'success': True,
                'coupon': CouponSerializer(coupon).data,
                'discount': discount
            })
        else:
            return Response({
                'success': True,
                'discount': 0,
                'message': '銘謝惠顧'
            })

    except Order.DoesNotExist:
        return Response({'error': '訂單不存在、非您本人或尚未完成'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Feedback submission/draw error for order {order_id}: {str(e)}")
        return Response({'error': '處理抽獎請求時發生錯誤'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

@csrf_exempt
def submit_rating(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            menu_id = data.get('menu_id')
            rating_value = data.get('rating') # 變數名改為 rating_value 以免與模型字段混淆

            if not menu_id or rating_value is None:
                return JsonResponse({'success': False, 'error': '缺少 menu_id 或 rating'}, status=400)

            if not request.session.session_key:
                request.session.create()
            user_session = request.session.session_key

            menu_item_instance = MenuItem.objects.get(id=menu_id) # 確保是 MenuItem

            rating_obj, created = MenuRating.objects.update_or_create(
                menu_item=menu_item_instance,
                user_session=user_session,
                defaults={'rating': rating_value}
            )
            logger.info(f"評分已保存或更新: {rating_obj} (Created: {created})") # 添加日誌
            return JsonResponse({'success': True, 'message': '評分已保存'})
        except MenuItem.DoesNotExist:
            logger.error(f"提交評分失敗: 找不到 ID 為 {menu_id} 的 MenuItem")
            return JsonResponse({'success': False, 'error': '找不到指定的菜單項目'}, status=404)
        except Exception as e:
            logger.error(f"提交評分時發生未預期錯誤: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': '無效的請求方法'}, status=405)

@api_view(['GET'])
def get_menu_ratings(request):
    try:
        # 使用 MenuItem 而不是 Menu
        menu_items = MenuItem.objects.annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings')
        ).values('id', 'name', 'avg_rating', 'rating_count')
        
        ratings_data = {}
        for item in menu_items:
            ratings_data[item['id']] = {
                'avg_rating': round(item['avg_rating'], 1) if item['avg_rating'] else 0,
                'rating_count': item['rating_count'] or 0
            }
        
        return JsonResponse(ratings_data)
    except Exception as e:
        print(f"獲取評分數據錯誤: {e}")
        return JsonResponse({})