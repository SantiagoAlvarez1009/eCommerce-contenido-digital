from django.contrib                import messages
from django.contrib.auth           import login
from django.contrib.auth.decorators import login_required
from django.shortcuts              import get_object_or_404, redirect, render
from django.views.decorators.http  import require_POST

from apps.cart.models                 import Cart
from apps.services.permissions.roles  import role_required
from .forms  import ProfileForm, RegisterForm, RoleForm
from .models import User


def register(request):
    if request.user.is_authenticated:
        return redirect('catalog:list')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        Cart.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, 'Cuenta creada correctamente.')
        return redirect('catalog:list')
    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Perfil actualizado.')
        return redirect('users:profile')
    return render(request, 'users/profile.html', {'form': form})


# --- Administration (ADMIN role) ---

@role_required(User.Role.ADMIN)
def user_list(request):
    users = User.objects.order_by('email')
    return render(request, 'users/manage_list.html', {
        'users': users,
        'form' : RoleForm(),
    })


@role_required(User.Role.ADMIN)
@require_POST
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
    else:
        user.set_enabled(not user.is_active)
        messages.success(request, f'Cuenta {"activada" if user.is_active else "desactivada"}: {user.email}.')
    return redirect('users:manage_list')


@role_required(User.Role.ADMIN)
@require_POST
def user_change_role(request, pk):
    user = get_object_or_404(User, pk=pk)
    form = RoleForm(request.POST)
    if user == request.user:
        messages.error(request, 'No puedes cambiar tu propio rol.')
    elif form.is_valid():
        user.role = form.cleaned_data['role']
        user.save(update_fields=['role'])
        messages.success(request, f'Rol de {user.email} actualizado a {user.get_role_display()}.')
    else:
        messages.error(request, 'Rol invalido.')
    return redirect('users:manage_list')
