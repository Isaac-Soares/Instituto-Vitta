from django.contrib import admin
from .models import Especialidade, Profissional, Consulta


@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'total_profissionais')
    search_fields = ('nome', 'descricao')

    @admin.display(description='Profissionais')
    def total_profissionais(self, obj):
        return obj.profissional_set.count()


@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    list_display = ('nome_exibicao', 'especialidade', 'registro')
    list_filter = ('especialidade',)
    search_fields = ('nome', 'registro', 'especialidade__nome')


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'profissional', 'data', 'horario', 'status')
    list_filter = ('status', 'data', 'profissional__especialidade', 'profissional')
    search_fields = ('paciente__username', 'paciente__email', 'profissional__nome')
    list_editable = ('status',)
    date_hierarchy = 'data'
    readonly_fields = ('criado_em',)
