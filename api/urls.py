from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EtudiantViewSet, OrphelinViewSet, InternationalViewSet,
    UniversiteViewSet, EliteViewSet, JamatViewSet, chatbot_view, chatbot_api,
    list_conversations, get_conversation_history, delete_conversation,
    delete_all_conversations
)

router = DefaultRouter()
router.register(r'etudiants', EtudiantViewSet)
router.register(r'orphelins', OrphelinViewSet)
router.register(r'international', InternationalViewSet)
router.register(r'universite', UniversiteViewSet)
router.register(r'elites', EliteViewSet)
router.register(r'jamat', JamatViewSet)

urlpatterns = [
    path('chatbot/', chatbot_view, name='chatbot'),
    path('chatbot/api/chat/', chatbot_api, name='chatbot_api'),
    path('chatbot/api/conversations/', list_conversations, name='list_conversations'),
    path('chatbot/api/conversations/<int:conversation_id>/', get_conversation_history, name='get_conversation_history'),
    path('chatbot/api/conversations/<int:conversation_id>/delete/', delete_conversation, name='delete_conversation'),
    path('chatbot/api/conversations/delete-all/', delete_all_conversations, name='delete_all_conversations'),
    path('', include(router.urls)),
]
