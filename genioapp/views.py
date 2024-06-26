from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django import forms
from django.utils import timezone
from .models import ClassRoom, Course, Student, InstructorProfile, StudentProfile, IntructorAvailability, CourseLevels, \
    CourseSession, StudentOrder
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404
import uuid
import re
import random
import time
from agora_token_builder import RtcTokenBuilder
import json
from .forms import InstructorSignUpForm, CourseForm, LoginForm, StudentForm, StudentCred, CourseLevelForm, \
    ClassRoomForm, InstructorAvailabilityForm, CourseSessionForm, CheckInstructorAvailability, GetSessionForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from square.client import Client
from pydantic import BaseModel
#Adding Payment Structure
CONFIG_TYPE = "SANDBOX"
client = Client(
    access_token='EAAAl8jGCWT2vmMOKKsTZy2m91S1jMkOrV2cIjL8ZXuFSFy_sEO2v94hR0dEEO-W',
    environment='sandbox')
result = client.locations.list_locations()
#print(result)


APPLICATION_ID = 'sandbox-sq0idb-O716r2ozEg1jrkgkFFszag'
ACCESS_TOKEN = 'EAAAl8jGCWT2vmMOKKsTZy2m91S1jMkOrV2cIjL8ZXuFSFy_sEO2v94hR0dEEO-W'
LOCATION_ID = 'LTXKVQTY01TSR'
PAYMENT_FORM_URL = (
    "https://web.squarecdn.com/v1/square.js"
    if CONFIG_TYPE == "PRODUCTION"
    else "https://sandbox.web.squarecdn.com/v1/square.js"
)
location = client.locations.retrieve_location(location_id=LOCATION_ID).body["location"]
ACCOUNT_CURRENCY = location["currency"]
ACCOUNT_COUNTRY = location["country"]


@csrf_exempt
def make_payment(request, id):
    idempotency_key=id
    #order = StudentOrder.objects.get(id=id)
    amtprice=4300
    #courselevels = CourseLevels.
    print("Course level price:",amtprice)
    #*float(price)
    return render(request, "genioapp/card_payment.html", {
        "PAYMENT_FORM_URL":PAYMENT_FORM_URL,
        "APPLICATION_ID": APPLICATION_ID,
        "LOCATION_ID": LOCATION_ID,
        "ACCOUNT_CURRENCY": ACCOUNT_CURRENCY,
        "ACCOUNT_COUNTRY": ACCOUNT_COUNTRY,
        "idempotency_key":idempotency_key,
        "amount":int(amtprice)
        
    })
#Function to display classrooms
@csrf_exempt
def joinClassRoom(request):
    rooms=ClassRoom.objects.all()
    return render(request, "genioapp/join_classroom.html", {"rooms": rooms})


@csrf_exempt
def enterClassRoom(request):
    return render(request)

@csrf_exempt
def createRoomMember(request):
    data = json.loads(request.body)
    user = User.objects.get(id=data['UID'])
    if is_instructor(user):
        member, created = ClassRoom.objects.get_or_create(
        name=user.first_name + user.last_name,
        uid=data['UID'],
        room_name=data['room_name'],
        user_role='Instructor')
    else:
        member, created = ClassRoom.objects.get_or_create(
            name=user.first_name + user.last_name,
            uid=data['UID'],
            room_name=data['room_name']
        )
    #print(member.user_role)
    return JsonResponse({
        'name': data['name'],
        'role':member.user_role}, safe=False)

class Payment(BaseModel):
    token: str
    idempotencyKey: str

@csrf_exempt
def process_payment(request):
    data = json.loads(request.body)
    #price=request.data['amount']
    # Charge the customer's card
    amount=data['amount']
    #print(data['token'])
    id=data['idempotencyKey']
    create_payment_response = client.payments.create_payment(
        body={
            "source_id": data['token'],
            "idempotency_key": data['idempotencyKey'],
            "amount_money": {
                "amount": int(amount),
                "currency": ACCOUNT_CURRENCY,
            },
        }
    )
    data=create_payment_response.body
    #data['payment']['status']

    if create_payment_response.is_success():
        order=StudentOrder.objects.get(id=id)
        order.completion_status="completed"
        payment_data=data["payment"]
        print(payment_data['id'])
        order.payment_id=payment_data['id']
        order.save()
        return JsonResponse(data)
    elif create_payment_response.is_error():
        return create_payment_response

def getRoomMember(request):
    uid = request.GET.get('UID')
    room_name = request.GET.get('room_name')

    member = ClassRoom.objects.get(
        uid=uid,
        room_name=room_name,
    )
    name = member.name
    return JsonResponse({'name': name}, safe=False)


@csrf_exempt
def deleteRoomMember(request):
    data = json.loads(request.body)
    member = ClassRoom.objects.get(
        name=data['name'],
        uid=data['UID'],
        room_name=data['room_name']
    )
    member.delete()
    return JsonResponse('Member deleted', safe=False)


def getAgoraToken(request, id):
    #appId = "9668f778f64048d494a10d36ab11e203"
    #appCertificate = "a8411d32d4f54dd4b6cd9a6dca80cfb9"
    #room_id= request.GET.get('id')
    channelName = ClassRoom.objects.get(id=id).room_name
    uid = request.user.id
    user_name=request.user.username
    expirationTimeInSeconds = 3600
    currentTimeStamp = int(time.time())
    privilegeExpiredTs = currentTimeStamp + expirationTimeInSeconds
    role = 1

    token = "token"
    #RtcTokenBuilder.buildTokenWithUid(appId, appCertificate, channelName, uid, role, privilegeExpiredTs)

    return JsonResponse({'token': token, 'uid': uid, 'room_name':channelName, 'user_name':user_name}, safe=False)


def lobby(request):
    return render(request, "genioapp/lobby.html")


def room(request):
    return render(request, "genioapp/videoApp/classRoom.html")


def about(request):
    return render(request, "genioapp/about.html")


def course_detail(request):
    return render(request, "genioapp/course_detail.html")


def is_age_appropriate(student_age, age_range):
    lower_bound, upper_bound = map(int, re.findall(r'\d+', age_range))
    print("LB:", lower_bound)
    print("UB", upper_bound)
    print("Age:", student_age)
    return lower_bound <= student_age <= upper_bound


def courseregistration(request):
    form = CourseForm(request.POST)
    print(form.data)

    if form.is_valid():
        form.save()
        return redirect('/')
    else:
        form = CourseForm()
    return render(request, "genioapp/courseregistrationpage.html", {"form": form})


def custom_login(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirect to a success page or any desired page after login
                # Example: return redirect('home')
                print(username)
                print(password)
                response = redirect("/")
                return response  # Redirect to the desired URL after successful login
    else:
        form = LoginForm()

    return render(request, "genioapp/login.html", {"form": form})


def is_instructor(user):
    val = user.groups.filter(name="Instructor").exists()
    print(val)
    return val


def is_student(user):
    val = user.groups.filter(name="Students").exists()
    print(val)
    return val


def viewCourses(request):
    if is_student(request.user):
        courses = Course.objects.all()
        courses_with_levels = []
        for course in courses:
            levels = course.courselevels_set.all()
            courses_with_levels.append({"course": course, "levels": levels})
        return render(
            request,
            "genioapp/courses.html",
            {"courses_with_levels": courses_with_levels},
        )
    else:
        return render(request, "genioapp/user_profile.html")


def create_course_session(request):
    if request.method == 'POST':
        form = CourseSessionForm(request.POST)
        form1 = CheckInstructorAvailability(request.POST or None)
        if form.is_valid():
            course_level = form.cleaned_data["course_level"]
            session = form.cleaned_data["session"]
            start_datetime = form.cleaned_data["start_datetime"]
            end_datetime = form.cleaned_data["end_datetime"]
            course_name = form.cleaned_data["course"].title
            course_level_name=course_level.name
            class_room = ClassRoom(
                room_name= course_name+"_"+course_level_name
            )
            class_room.save()

            course_session = CourseSession(
                course_level=course_level,
                session=session,
                start_datetime=start_datetime,
                end_datetime=end_datetime)
            course_session.save()
            return redirect("/")

            form.save()  # You might want to customize this based on your logic
            return redirect('/')
        print(form1.data)
        if form1.is_bound:
            availability_data = []
            availability=[]
            instructor_name = form1.data['instructor']
            print(instructor_name)
            print(len(instructor_name))
            if len(instructor_name)<=1:
                availability = IntructorAvailability.objects.filter(
                    instructor=InstructorProfile.objects.get(id=instructor_name)).values('id', 'day', 'start_time',
                                                                                           'end_time', 'available')

            availability_data = [
                {'day': av['day'], 'start_time': av['start_time'], 'end_time': av['end_time'],
                 'available': av['available']} for av in availability
            ]
            return render(request, 'genioapp/sessions.html',
                          {'form': form, 'form1': form1, 'availability_data': availability_data})
        else:
            return render(request, 'genioapp/sessions.html', {'form': form, 'form1': form1})
    else:
        form = CourseSessionForm()
        form1 = CheckInstructorAvailability(request.POST or None)

    return render(request, 'genioapp/sessions.html', {'form': form, 'form1': form1})


def get_course_levels(request):
    course_id = request.GET.get('course_id')
    levels = CourseLevels.objects.filter(course_id=course_id).values('id', 'name')
    return JsonResponse(list(levels), safe=False)


def get_instructor(request):
    course_id = request.GET.get('course_id')
    instructor = InstructorProfile.objects.filter(course=Course.objects.get(id=course_id)).values('first_name',
                                                                                                  'last_name')
    print(instructor)
    # prinr(instructor.first_name)
    return JsonResponse(list(instructor), safe=False)


def init_ins_availability(instructor):
    insa = IntructorAvailability(instructor=instructor)
    insa.save()


def view_ins_availability(request):
    user = request.user
    try:
        instructor_profile = InstructorProfile.objects.get(user=user)
        # instructor_profile_id = instructor_profile.pk
        InsFormSet = forms.inlineformset_factory(InstructorProfile, IntructorAvailability, fields="__all__", extra=0)
        if request.method == "POST":
            formset = InsFormSet(request.POST, request.FILES, instance=instructor_profile)
            if formset.is_valid():
                formset.save()
                return redirect('/viewinsavailability/')
        else:
            formset = InsFormSet(instance=instructor_profile)
            return render(request, 'genioapp/insavailability.html', {
                'form': formset})
    except InstructorProfile.DoesNotExist:
        # instructor_profile_id = None
        return render(request, 'genioapp/index.html')


def add_availability(request):
    instructor_profile = InstructorProfile.objects.get(user=request.user)
    insa = IntructorAvailability(
        instructor=instructor_profile,
        start_time='15:00',
        end_time='16:00'
    )
    insa.save()
    return redirect('/viewinsavailability/')


def addcourselevels(request):
    form = CourseLevelForm(request.POST)
    if form.is_valid():
        form.save()
    else:
        form = CourseLevelForm()

    return render(request, "genioapp/courseregistrationpage.html", {"form": form})


@login_required(login_url="/login")
def instructorsignup(request):
    if request.method == "POST":
        form = InstructorSignUpForm(request.POST,
                                    request.FILES)
        # Make sure to include request.FILES for handling uploaded files
        if form.is_valid():
            print(form.data)
            user = form.save()
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data.get("last_name")
            email = form.cleaned_data.get("email")
            bio = form.cleaned_data.get("bio")
            language = form.cleaned_data.get("language")

            # Additional validation for image file

            instructor = InstructorProfile(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                bio=bio,
                language=language
            )
            instructor.save()

            instructor_group = Group.objects.get(name="Instructor")
            user.groups.add(instructor_group)

            init_ins_availability(instructor)

            return render(request, "genioapp/index.html")
    else:
        form = InstructorSignUpForm()

    return render(request, "genioapp/InstructorSignup.html", {"form": form})


def validate_image_file(image):
    if image:
        if not image.content_type.startswith('image'):
            raise ValidationError('File is not an image.')
        # Add more checks as needed (e.g., file size, dimensions, etc.)


def index(request):
    # Retrieve the list of categories from the database and order them by ID
    courses_with_levels = []
    # if is_student(request.user):
    courses = Course.objects.all()
    # courses_with_levels = []
    for course in courses:
        levels = course.courselevels_set.all()
        courses_with_levels.append({"course": course, "levels": levels})
    return render(
        request,
        "genioapp/index.html",
        {"courses_with_levels": courses_with_levels}
    )


# @login_required
# def about(request):
#     heading = "This is a Distance Education Website! Search our Categories to find all available Courses."
#     return render(request, "genioapp/about.html", {"heading": heading})


def course_by_id(request, course_id):
    course = Course.objects.get(id=course_id)
    courselevels = []
    courselevels=CourseLevels.objects.filter(course=course)
    session_list=[]
    for level in courselevels:
        sessions=CourseSession.objects.filter(course_level=level)
        session_list.append({"level":level,"sessions":sessions})
    print(session_list)
    return render(
        request,
        "genioapp/course_detail.html",
        {"course": course,
         "levels":courselevels,
         "session_list":session_list},
    )

#@login_required(login_url="/login/")
def courses(request):
    
    courses_with_levels = []
    # if is_student(request.user):
    courses = Course.objects.all()
    # courses_with_levels = []
    for course in courses:
        levels = course.courselevels_set.all()
        sessions=[]
        for level in levels:
            sessionlist=level.coursesession_set.all()
            sessions.append({"level": level, "sessions":sessionlist})
        name=course.instructor.user.first_name+ " "+course.instructor.user.last_name
        courses_with_levels.append({"course": course, "levels": levels, "sessions":sessions, "name":name})
    return render(request, "genioapp/courses.html", {"courses_with_levels": courses_with_levels})


def custom_logout(request):
    logout(request)
    return redirect("/login/")


def student_form(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_bound:
            user = form.save()
            name = form.cleaned_data.get('name')
            email = form.cleaned_data.get('email')
            age = form.cleaned_data.get('age')
            phone = form.cleaned_data.get('phone')
            gender = form.cleaned_data.get('gender')

            student = StudentProfile(
                user=user,
                name=name,
                email=email,
                age=age,
                gender=gender,
                phone=phone,
            )
            student.save()
            # student.delete()

            student_group = Group.objects.get(name="Students")
            user.groups.add(student_group)
            return redirect("/")  # Redirect to the admin view
    else:
        form = StudentForm()

    return render(request, "genioapp/student_form.html", {"form": form})


def admin_students_list(request):
    students = Student.objects.all()
    return render(request, "genioapp/admin_students_list.html", {"students": students})


def create_credentials(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    name = student.name
    email = student.email
    age = student.age
    gender = student.gender
    phone = student.phone

    if request.method == "POST":
        form = StudentCred(request.POST)
        if form.is_valid():
            user = form.save()
            studentProfile = StudentProfile(
                user=user,
                name=name,
                email=email,
                age=age,
                gender=gender,
                phone=phone,
            )
            studentProfile.save()
            student.delete()

            student_group = Group.objects.get(name="Students")
            user.groups.add(student_group)
            return redirect("/admin_students_list/")
    else:
        form = StudentCred(request.POST)

    return render(
        request,
        "genioapp/create_credentials.html",
        {"form": form, "student_id": student_id},
    )  # Redirect back to the admin view


# def get_instructor_availability(request):
@login_required(login_url="/student_form/")
def createorder(request, course_level_id):
    courselevels = CourseLevels.objects.get(id=course_level_id)
    student = StudentProfile.objects.get(user=request.user)
    course = courselevels.course
    # Check if a StudentOrder already exists for the given course_level and student
    order = StudentOrder.objects.filter(course_level=courselevels, student=student).first()
    if not order:
        order = StudentOrder(student=student, course_level=courselevels, completion_status='ongoing')
        order.save()
    ordercompleted = False
    if order.completion_status == 'completed':
        ordercompleted = True
    #print(existing_order.completion_status)
    if request.method == "POST":
        # If no order exists, create a new StudentOrder
        idempotency_key=order.id
        amtprice=order.course_level.price*100
        print("Course level price:",amtprice)
        return render(request, "genioapp/card_payment.html", {
            "PAYMENT_FORM_URL":PAYMENT_FORM_URL,
            "APPLICATION_ID": APPLICATION_ID,
            "LOCATION_ID": LOCATION_ID,
            "ACCOUNT_CURRENCY": ACCOUNT_CURRENCY,
            "ACCOUNT_COUNTRY": ACCOUNT_COUNTRY,
            "idempotency_key":idempotency_key,
            "amount":int(amtprice)
        })
        #return redirect("/")
    else:
        return render(request, 'genioapp/order.html', {'course': course, 'courselevels': courselevels,
                                                   'ordercompleted': ordercompleted})


def user_profile(request):
    user = request.user
    if is_student(user):
        student = StudentProfile.objects.get(user=user)
        student_orders = StudentOrder.objects.filter(student=student)

        stu_course_levels = []
        for student_order in student_orders:
            if student_order.completion_status == 'ongoing':
                continue
            course_level = student_order.course_level
            course = course_level.course
            sessions = CourseSession.objects.filter(course_level=course_level)
            classrooms = []
            for sess in sessions:
                room = ClassRoom.objects.filter(coursesession=sess)
                classrooms.append(room)
                #print(room)
            stu_course_lvl = {
                "course_title": course.title,
                "course_level": course_level.name,
                "sessions": sessions,
                "classrooms":classrooms,
            }

            stu_course_levels.append(stu_course_lvl)
            
        profile_data = {
            'username': user.username,
            'group': 'Student',
            'name': student.name,
            'age': student.age,
            'email': student.email,
            'gender': student.gender,
            'phone': student.phone,
            'stu_course_levels': stu_course_levels
        }
        #print(stu_course_levels)
    elif is_instructor(user):
        instructor_profile = InstructorProfile.objects.get(user=user)

        # Get courses taught by the instructor
        courses_taught = Course.objects.filter(instructor=instructor_profile)

        # Get course levels for each course
        instructor_course_levels = []
        for course in courses_taught:
            levels = CourseLevels.objects.filter(course=course)
            instructor_course_levels.append({'course': course, 'levels': levels})

        # Get session details for each course level
        session_details = []
        for course_level in CourseLevels.objects.filter(course__in=courses_taught):
            sessions = CourseSession.objects.filter(course_level=course_level)
            session_details.append({'course_level': course_level, 'sessions': sessions})

        profile_data = {
            'username': user.username,
            'group': 'Instructor',
            'name': instructor_profile.first_name + ' ' + instructor_profile.last_name,
            'email': instructor_profile.email,
            'bio': instructor_profile.bio,
            'language': instructor_profile.language,
            'courses_taught': instructor_course_levels,
            'session_details': session_details,
            # Add other instructor-specific data
        }
    else:
        profile_data = {
            'username': user.username,
            'group': 'Other',
        }

    return render(request, "genioapp/user_profile.html", {"profile_data": profile_data})
