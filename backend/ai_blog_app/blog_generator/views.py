from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytube import YouTube
from django.conf import settings
import os
import assemblyai as aai
import openai # you can use open ai but i am using the Groq 
from groq import Groq # using Groq instead of openai
import yt_dlp
from .models import BlogPost
# Create your views here.



@login_required
def index(request):
    return render(request, 'index.html')

def user_login(request):
     if request.method == 'POST':
          username = request.POST['username']
          password = request.POST['password']

          user = authenticate(request,username=username,password=password)
          if user is not None:
              login(request, user)
              return redirect('/')
          else:
            error_message = 'Error Logging in'
            return render(request, 'login.html', {'error_message':error_message})

         
     return render(request, 'login.html')


def yt_title(link):
    # yt = YouTube(link)
    # title = yt.title
    try:
        ydl_opts = {
            'quiet': True,
            'force_generic_extractor': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=False)
            title = info_dict.get('title', 'Unknown Title')
            print(f"Title: {title}")
            return title
    except Exception as e:
        print(f"Error fetching title: {e}")
        return "Error fetching title"

# This won't work because of the bug in the pytube package, see official github page of pytube for more info.

# def download_audio(link):
#     yt = YouTube(link)
#     video = yt.streams.filter(only_audio=True).first()
#     out_file = video.download(output_path=settings.MEIDA_ROOT)
#     base , ext = os.path.splitext(out_file)
#     new_file = base + '.mp3'
#     os.rename(out_file,new_file)
#     return new_file

def download_audio(link):
    ydl_opts = {
        'format': 'bestaudio/best',  
        'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'), 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  
            'preferredcodec': 'mp3',
            'preferredquality': '192', 
        }],
        'quiet': True,  
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3')
            return filename
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None



def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = 'yourapi'
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    #print(f'Transcript: {transcript.text}')
    return transcript.text

def generate_blog_from_transcription(transcription):
    try:
        client = Groq(
        api_key="your api",  # This is the default and can be omitted
    )
        
        prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcript, but dont make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

        chat_completion = client.chat.completions.create(
            model="llama3-8b-8192",  # Specify the model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
            top_p=0.95
        )
        #answer = completion.choices[0].message.content.strip()  # Extract the generated answer
        generated_content = chat_completion.choices[0].message.content.strip()
        print(f'Grog: {chat_completion.choices[0].message.content}')
        return generated_content
    except:
        print('not able to connect')
        return JsonResponse({'error':'Not able to fetch the Resutls from the GRoq '}, status=400)
        



@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
            JsonResponse({'content':yt_link})
        except(KeyError,json.JSONDecodeError):
            return JsonResponse({'error':'Invalid data sent'}, status=400)
        
        # get title of the video

        title = yt_title(yt_link)

        # get the transcript of the video

        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error':'Failed to get the transcription'},status=500)


        # Generate blog using openai 
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error':'Failed to get the transcription from groq'},status=500)
        

        # save the blog article to database
        new_blog_article = BlogPost.objects.create(
            user = request.user,
            youtube_title = title,
            youtube_link = yt_link,
            generated_content = blog_content,
        )

        new_blog_article.save()


        # return the blog article for display
        if isinstance(blog_content, JsonResponse):
            return blog_content  # Directly return it if it's already a JsonResponse

        return JsonResponse({'content': blog_content})  # Wrap it in JsonResponse only if needed


    else:
        return JsonResponse({'error':'Invalid request method'}, status=405)

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatpassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username,email,password)
                user.save()
                login(request,user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message':error_message})
        else:
            error_message = 'Password dont match'
            return render(request,'signup.html',{error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

def blog_list(request):

    blog_articles = BlogPost.objects.filter(user=request.user)

    return render(request,'all-blogs.html',{'blog_articles':blog_articles})


def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)

    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html',{'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')