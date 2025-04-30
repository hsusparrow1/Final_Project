"""
URL configuration for Final_Project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from Website import views
from django.conf import settings
from django.conf.urls.static import static
from Website.views import get_orders, update_order_status, update_menu_item_status

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.page1, name='home'),
    path('api/menu/', views.MenuItemListAPIView.as_view(), name='menu-item-list'),  # API 列表，獲取所有餐點
    path('api/menu/<int:id>/', views.MenuItemDetailAPIView.as_view(), name='menu-item-detail'),  # API 詳情，根據 ID 獲取單個餐點
    path('page2_menu/', views.page2_menu, name='page2_menu'),  # 這裡是對應的路徑
    path('page3_shopping_cart/', views.page3_shopping_cart, name='page3_shopping_cart'),  # 新增結帳頁面路由
    path('api/save-cart/', views.save_cart, name='save_cart'),
    path('api/get-cart/', views.get_cart, name='get_cart'),
    path('api/menu/<int:id>/', views.MenuItemDetailAPIView.as_view(), name='menu-item-detail'),
# ... 其他路由 ...
    path('api/submit-order/', views.submit_order, name='submit_order'),
    path('api/orders/', get_orders, name='get_orders'),
    path('api/orders/<uuid:order_id>/status/', update_order_status, name='update_order_status'),
    path('api/menu/<int:item_id>/status/', update_menu_item_status, name='update_menu_item_status'),
]

urlpatterns += [
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('page4_order_confirmation/', views.page4_order_confirmation, name='page4_order_confirmation'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
