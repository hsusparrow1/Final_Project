from rest_framework import serializers
from .models import MenuItem, Feedback, Coupon
from django.db import transaction, connection


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = '__all__'

    def create(self, validated_data):
        """確保新增的商品 ID 連續"""
        with transaction.atomic():
            # 找出第一個空缺的 ID
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COALESCE(
                            (SELECT MIN(t1.id + 1)
                            FROM Website_menuitem t1
                            LEFT JOIN Website_menuitem t2 ON t1.id + 1 = t2.id
                            WHERE t2.id IS NULL AND t1.id + 1 > 0), 
                            1
                        ) AS next_id
                """)
                result = cursor.fetchone()
                next_id = result[0] if result and result[0] else 1

            # 創建新商品並指定 ID
            return MenuItem.objects.create(id=next_id, **validated_data)


# 新增在 serializers.py
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['order', 'rating']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'
