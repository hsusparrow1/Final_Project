from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path
from Website import views
from django.conf import settings
from django.conf.urls.static import static
from Website.views import page0, login_view, register_view, logout_view, check_auth, get_orders, update_order_status, \
    update_menu_item_status, admin_dashboard_login, admin_dashboard_auth, admin_dashboard

urlpatterns = [
    # 管理後台
    path('admin/', admin.site.urls, name='admin'),  # Django 內建管理後台
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),  # 店家自訂管理頁面

    # 認證相關路由
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('api/check-auth/', check_auth, name='check_auth'),

    # 前台頁面路由
    path('', page0, name='home'),  # 登入首頁
    path('page1/', views.page1, name='page1'),  # 內用外帶
    path('page2_menu/', views.page2_menu, name='page2_menu'),  # 菜單頁面
    path('page3_shopping_cart/', views.page3_shopping_cart, name='page3_shopping_cart'),  # 購物車頁面
    path('page4_order_confirmation/', views.page4_order_confirmation, name='page4_order_confirmation'),  # 訂單確認頁面
    path('page5_order_status/', views.page5_order_status, name='page5_order_status'),  # 訂單狀態頁面

    # 菜單相關 API
    path('api/menu/', views.MenuItemListAPIView.as_view(), name='menu-item-list'),  # 獲取所有餐點/新增餐點
    path('api/menu/<int:id>/', views.MenuItemDetailAPIView.as_view(), name='menu-item-detail'),  # 獲取/刪除單個餐點
    path('api/menu/<int:item_id>/status/', update_menu_item_status, name='update_menu_item_status'),  # 更新餐點狀態(售完/可售)

    # 購物車相關 API
    path('api/save-cart/', views.save_cart, name='save_cart'),  # 儲存購物車內容
    path('api/get-cart/', views.get_cart, name='get_cart'),  # 獲取購物車內容

    # 訂單相關 API
    path('api/submit-order/', views.submit_order, name='submit_order'),  # 提交訂單
    path('api/orders/', get_orders, name='get_orders'),  # 獲取所有訂單列表
    path('api/orders/<uuid:order_id>/', views.get_order_detail, name='order-detail'),  # 獲取/刪除單個訂單詳情
    path('api/orders/<uuid:order_id>/status/', update_order_status, name='update_order_status'),  # 更新訂單狀態
    path('api/orders/<uuid:order_id>/delete/', views.delete_order, name='delete_order'),
    path('api/orders/completed/delete/', views.delete_completed_orders, name='delete_completed_orders'),
    
    # 評價與折價券相關 API
    path('api/submit-feedback/', views.submit_feedback, name='submit_feedback'),  # 重要：確保這行存在
    path('api/get-coupons/', views.get_user_coupons, name='get_user_coupons'),
    path('api/menu-ratings/', views.get_menu_ratings, name='get_menu_ratings'),
    
    # 管理後台登入路由（公開訪問）
    path('admin_dashboard/login/', admin_dashboard_login, name='admin_dashboard_login'),
    path('admin_dashboard/auth/', admin_dashboard_auth, name='admin_dashboard_auth'),

    # 保護的管理後台主頁（需要登入）
    path('admin_dashboard/', login_required(admin_dashboard, login_url='/admin_dashboard/login/'),
         name='admin_dashboard'),
    path('page6_feedback/', views.page6_feedback, name='page6_feedback'),
    path('api/submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/get-coupons/', views.get_user_coupons, name='get_coupons'),
    path('api/menu-ratings/', views.get_menu_ratings, name='menu_ratings'),
]

# 在開發環境中提供媒體文件服務
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
