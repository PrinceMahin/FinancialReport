from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib import auth
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .utils import token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator


# from django.template.loader import render_to_string


# Create your views here.
class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        if not validate_email(email):
            return JsonResponse({'email_error': ' email is not valid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': ' Sorry Email is exits'}, status=409)
        return JsonResponse({'email_valid': True})


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']
        if not str(username).isalnum():
            return JsonResponse({'username_error': ' user name should contain alphanumeric characters'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': ' Sorry User name is exits'}, status=409)
        return JsonResponse({'username_valid': True})


class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'password is too short')
                    return render(request, 'authentication/register.html')

                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()

                # parth_to_view
                # for domain
                # relative url verification
                # token
                # encode uid

                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                domain = get_current_site(request).domain

                link = reverse('activate', kwargs={
                    'uidb64': uidb64, 'token': token_generator.make_token(user)})

                active_url = 'http://' + domain + link

                email_subject = 'Activate Your Account'
                email_body = 'Hi\n ' + user.username + ' Please Use this link to Activate your account\n' + active_url

                # template = render_to_string('base/email_template.html', {'username':request.user.profile.username})
                email = EmailMessage(
                    email_subject,
                    email_body,
                    settings.EMAIL_HOST_USER,
                    ['dontreply@gmail.com'],
                    [email],
                )
                email.fail_silently = False
                email.send()
                messages.success(request, 'Your account is successfully Registered')
                return render(request, 'authentication/register.html')

        return render(request, 'authentication/register.html')


class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not token_generator.check_token(user, token):
                return redirect('login' + '?message=' + 'User is Already Activated')

            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()

            messages.success(request, 'Account has been activated ')
            return redirect('login')

        except Exception as ex:
            pass

        return redirect('login')


class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']

        if username and password:
            user = auth.authenticate(username=username, password=password)

            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, 'Welcome " ' + user.username + '". You are now Logged in')
                    return redirect('expenses')

                messages.error(request, 'Account is not active, Please Check Your Email')
                return render(request, 'authentication/login.html')
            messages.error(request, 'Invalid!! Try again !! ')
            return render(request, 'authentication/login.html')
        messages.error(request, 'Please Fill-up All Fields ')
        return render(request, 'authentication/login.html')


class LogoutView(View):
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'You have been logged out')
        return redirect('login')


class RequestPasswordResetEmail(View):
    def get(self, request):
        return render(request, 'authentication/reset-password.html')

    def post(self, request):
        email = request.POST['email']

        context = {
            'values': request.POST
        }

        if not validate_email(email):
            messages.error(request, 'Please supply a valid email')
            return render(request, 'authentication/reset-password.html', context)

        current_site = get_current_site(request)
        user = User.objects.filter(email=email)

        if user.exists():
            email_contents = {
                'user': user[0],
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token': PasswordResetTokenGenerator().make_token(user[0])
            }
            link = reverse('reset-user-password', kwargs={
                'uidb64': email_contents['uid'], 'token': token_generator.make_token(user[0])})

            reset_url = 'http://' + current_site.domain + link

            email_subject = 'Password Rest'
            email_body = 'Hi \n ' 'THERE'  ' Please Use this link to Reset-password of your account \n' \
                         + reset_url

            email = EmailMessage(
                email_subject,
                email_body,
                settings.EMAIL_HOST_USER,
                ['dontreply@gmail.com'],
                [email],
            )
            email.send(fail_silently=False)
            messages.success(request, ' we have sent you an email to rest ur password')
        else:

            messages.success(request, ' we have sent you an email to rest ur password')

        return render(request, 'authentication/reset-password.html')


class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        # try:
        #     user_id = force_str(urlsafe_base64_decode(uidb64))
        #     user = User.objects.get(pk=user_id)
        #
        #     if not PasswordResetTokenGenerator().check_token(user, token):
        #         messages.info(request, ' This Link is old , Use The new link')
        #         return render(request, 'authentication/reset-password.html')
        #
        # except Exception as identifier:
        #
        #     pass
        #

        return render(request, 'authentication/set-newpassword.html', context)

    def post(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }

        password = request.POST['password']
        password2 = request.POST['password2']

        if password != password2:
            messages.error(request, 'password is not matching')
        if len(password) < 6:
            messages.error(request, 'password is too short')
            return render(request, 'authentication/set-newpassword.html', context)

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            user.set_password(password)
            user.save()
            messages.success(request, ' password rest successfull, Use New Password')
            return redirect('login')
        except Exception as identifier:
            messages.info(request, ' Something is Wrong')
            return render(request, 'authentication/set-newpassword.html', context)
