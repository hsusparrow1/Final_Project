from rest_framework import serializers
from .models import MenuItem

class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = '__all__'  # 包含所有字段
        # 或者可以明確指定字段：
        # fields = ['id', 'name', 'category', 'description', 'price', 'image']