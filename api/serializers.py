from rest_framework import serializers
from main.models import Etudiant, Orphelin, International, Universite, Elite, Jamat
from .models import ChatConversation, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'is_user', 'content', 'timestamp']

class ChatConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatConversation
        fields = ['id', 'title', 'created_at']

class EtudiantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etudiant
        fields = '__all__'

class OrphelinSerializer(serializers.ModelSerializer):
    identifiant = EtudiantSerializer(read_only=True)
    class Meta:
        model = Orphelin
        fields = '__all__'

class InternationalSerializer(serializers.ModelSerializer):
    international = EtudiantSerializer(read_only=True)
    class Meta:
        model = International
        fields = '__all__'

class UniversiteSerializer(serializers.ModelSerializer):
    universite = EtudiantSerializer(read_only=True)
    class Meta:
        model = Universite
        fields = '__all__'

class EliteSerializer(serializers.ModelSerializer):
    identifiant = EtudiantSerializer(read_only=True)
    class Meta:
        model = Elite
        fields = '__all__'

class JamatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jamat
        fields = '__all__'
