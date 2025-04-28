from django.shortcuts import render
from rest_framework import generics
from .models import MenuItem
from .serializers import MenuItemSerializer

# 你原本的頁面視圖 (保持不變)
def page1(request):
    return render(request, 'page1.html')

def page2_menu(request):
    return render(request, 'page2_menu.html')  # 渲染 page2_menu.html 頁面

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