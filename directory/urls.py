from django.urls import path
from . import views

app_name = 'directory'

urlpatterns = [
    path('', views.search_view, name='search'),
    path('services/', views.services_view, name='services'),
    path('orgs/', views.org_list_view, name='org_list'),
    path('org/<int:org_id>/', views.org_detail_view, name='org_detail'),
]
