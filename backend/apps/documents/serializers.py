from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'uuid', 'case', 'title', 'document_type', 'file',
            'file_size', 'file_size_display', 'mime_type', 'description',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'file_size', 'mime_type', 'uploaded_by', 'uploaded_at', 'updated_at']

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else None

    def get_file_size_display(self, obj):
        if not obj.file_size:
            return None
        size = obj.file_size
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} ТБ'

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)
