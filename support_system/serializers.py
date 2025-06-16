from rest_framework import serializers
from .models import Ticket, TicketMessage, Notification, User

class UserShortSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

class TicketSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)
    support_user = UserShortSerializer(read_only=True)
    support_user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_support=True),
        source='support_user',
        required=False,
        write_only=True,
        allow_null=True
    )
    class Meta:
        model = Ticket
        fields = '__all__'
        extra_fields = ['support_user_id']
        read_only_fields = ['user', 'support_user']
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['support_user_id'] = instance.support_user.id if instance.support_user else None
        return data

class TicketMessageSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)
    text = serializers.CharField(source='content')
    class Meta:
        model = TicketMessage
        fields = ['id', 'ticket', 'user', 'text', 'created_at']
        read_only_fields = ['ticket']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__' 