from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import filters
from .models import Ticket, TicketMessage, Notification, User
from .serializers import TicketSerializer, TicketMessageSerializer, NotificationSerializer, UserShortSerializer
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Получить список заявок",
        operation_description="Получение списка заявок",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Фильтр по статусу заявки: open (открыт), in-progress (в работе), closed (закрыт)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response("Список заявок успешно получен", TicketSerializer(many=True))
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Создать новую заявку",
        operation_description="Создает новую заявку от имени текущего пользователя",
        request_body=TicketSerializer,
        responses={
            201: openapi.Response("Заявка успешно создана", TicketSerializer()),
            400: "Некорректные данные запроса"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        if getattr(self, 'swagger_fake_view', False):
            return Ticket.objects.all()

        queryset = Ticket.objects.all()

        if user.is_support:
            queryset = queryset.filter(support_user=user)
        elif not user.is_admin:
            queryset = queryset.filter(user=user)

        status_filter = self.request.query_params.get('status', None)

        STATUS_MAPPING = {
            'открыт': 'open',
            'в работе': 'in-progress',
            'закрыт': 'closed',
        }

        if status_filter:
            db_status = STATUS_MAPPING.get(status_filter.lower(), None)
            if db_status:
                queryset = queryset.filter(status=db_status)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Ticket.objects.all()

    def get_queryset(self):
        user = self.request.user

        if getattr(self, 'swagger_fake_view', False):
            return Ticket.objects.all()

        queryset = Ticket.objects.all()

        if user.is_support:
            queryset = queryset.filter(support_user=user)  
        elif not user.is_admin:
            queryset = queryset.filter(user=user)

        return queryset

    @swagger_auto_schema(
        operation_summary="Получить подробную информацию о заявке",
        operation_description="Получение подробной информации о конкретной заявке по ее ID",
        responses={
            200: openapi.Response("Детали заявки успешно получены", TicketSerializer()),
            404: "Заявка не найдена"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Полностью обновить заявку",
        operation_description="Полностью обновляет информацию о заявке по ее ID. Требуются все поля заявки",
        request_body=TicketSerializer,
        responses={
            200: openapi.Response("Заявка успешно обновлена", TicketSerializer()),
            400: "Некорректные данные запроса",
            404: "Заявка не найдена"
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Частично обновить заявку",
        operation_description="Частично обновляет информацию о заявке по ее ID. Позволяет обновить одно или несколько полей (например, назначить специалиста)",
        request_body=TicketSerializer(partial=True),
        responses={
            200: openapi.Response("Заявка успешно обновлена (частично)", TicketSerializer()),
            400: "Некорректные данные запроса",
            404: "Заявка не найдена"
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Удалить заявку",
        operation_description="Удаляет заявку по ее ID",
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                description="ID заявки для удаления"
            ),
        ],
        responses={
            204: "Заявка успешно удалена",
            404: "Заявка не найдена"
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

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
        # Уведомление специалисту о назначении заявки
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

    @swagger_auto_schema(
        operation_summary="Просмотреть сообщения по заявке",
        operation_description="Получение истории сообщений для конкретной заявки",
        manual_parameters=[
            openapi.Parameter(
                'ticket_id',
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                description="ID заявки, для которой нужно получить историю сообщений"
            ),
        ],
        responses={
            200: openapi.Response("История сообщений успешно получен", TicketMessageSerializer(many=True)),
            404: "Заявка не найдена"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Добавить новое сообщение в заявку",
        operation_description="Добавляет новое сообщение (ответ от администратора) в рамках заявки",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['text'],
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description="Текст сообщения")
            }
        ),
        responses={
            201: openapi.Response("Сообщение успешно добавлено", TicketMessageSerializer()),
            400: "Некорректные данные сообщения",
            404: "Заявка не найдена"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        ticket_id = self.kwargs['ticket_id']
        return TicketMessage.objects.filter(ticket_id=ticket_id)

    def perform_create(self, serializer):
        ticket = get_object_or_404(Ticket, id=self.kwargs['ticket_id'])
        serializer.save(user=self.request.user, ticket=ticket)

class SupportUserListView(generics.ListAPIView):
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.filter(is_support=True)
    filter_backends = []

    @swagger_auto_schema(
        operation_summary="Получить список всех специалистов поддержки",
        operation_description="Получение списка всех специалистов поддержки",
        responses={
            200: openapi.Response("Список специалистов поддержки успешно получен", UserShortSerializer(many=True))
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class UserListView(generics.ListAPIView):
    serializer_class = UserShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    filter_backends = []

    @swagger_auto_schema(
        operation_summary="Получить список всех пользователей",
        operation_description="Получение списка всех пользователей",
        responses={
            200: openapi.Response("Список пользователей успешно получен", UserShortSerializer(many=True))
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs) 