from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Ticket, TicketMessage, Notification, User
from .serializers import TicketSerializer, TicketMessageSerializer, NotificationSerializer, UserShortSerializer
from django.shortcuts import get_object_or_404

class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_support or user.is_admin:
            return Ticket.objects.filter(support_user=user) | Ticket.objects.filter(user=user)
        return Ticket.objects.filter(user=user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Ticket.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        # Только админ может назначать специалиста
        if 'support_user_id' in data:
            if not request.user.is_admin:
                return Response({'detail': 'Только администратор может назначать специалиста.'}, status=403)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Уведомление специалисту о назначении
        if 'support_user_id' in data and data['support_user_id']:
            Notification.objects.create(
                user=serializer.instance.support_user,
                ticket=serializer.instance,
                type='ticket_assigned',
                text=f'Вам назначена заявка #{serializer.instance.id}'
            )
        return Response(serializer.data)

class TicketMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        ticket_id = self.kwargs['ticket_id']
        return TicketMessage.objects.filter(ticket_id=ticket_id)
    def perform_create(self, serializer):
        ticket = get_object_or_404(Ticket, id=self.kwargs['ticket_id'])
        serializer.save(user=self.request.user, ticket=ticket)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})

class SupportUserListView(generics.ListAPIView):
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return User.objects.filter(is_support=True)

class UserListView(generics.ListAPIView):
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all() 