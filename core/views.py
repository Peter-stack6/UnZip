import base64, zipfile, tarfile, lzma, bz2, gzip, py7zr, rarfile, io, os, tempfile

from collections import defaultdict

from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt

from .forms import Upload
from .utils import detect_mime

def HomePage(request):
    context = {
        "meta_desc": "Welcome to our free online file tool! Upload, analyze, and manage various archive formats like ZIP, RAR, 7Z, and more, all with ease."
    }
    return render(request, "index.html", context)

def build_tree(paths):
    tree = lambda: defaultdict(tree)
    root = tree()
    for path in paths:
        parts = path.strip('/').split('/')
        current = root
        for part in parts:
            current = current[part]
    return root

def flatten_tree(tree):
    def recurse(t):
        return {k: recurse(v) if v else {} for k, v in t.items()}
    return recurse(tree)

def UploadFile(request):
    if request.method == 'POST':
        form = Upload(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]

            extracted_paths = []
            mime_type = detect_mime(uploaded_file)

            file_bytes = io.BytesIO(uploaded_file.read())
            file_bytes.seek(0)
            content = file_bytes

            tree = False
            encrypted = False

            try:
                match mime_type:
                    case 'application/zip' | 'application/x-zip-compressed':
                        with zipfile.ZipFile(file_bytes) as zip_ref:
                            is_encrypted = any(zinfo.flag_bits & 0x1 for zinfo in zf.infolist())
                            tree = True

                            if not is_encrypted:
                                extracted_paths = zip_ref.namelist()
                            else:
                                encrypted = True
                                

                    case 'application/x-tar':
                        with tarfile.open(fileobj=file_bytes, mode='r:*') as tar_ref:
                            extracted_paths = [m.name for m in tar_ref.getmembers() if m.name and not m.isdir()]
                            tree = True

                    case 'application/x-gzip':
                        if uploaded_file.name.endswith('.tar.gz'):
                            with tarfile.open(fileobj=file_bytes, mode='r:*') as tar_ref:
                                extracted_paths = [m.name for m in tar_ref.getmembers() if m.name and not m.isdir()]
                                tree = True
                        else:
                            tree = False
                            with gzip.open(file_bytes, 'rb') as f:
                                decompressed = f.read()
                                content = io.BytesIO(decompressed)

                    case 'application/x-bzip2':
                        tree = False
                        with bz2.open(file_bytes, 'rb') as f:
                            decompressed = f.read()
                            content = io.BytesIO(decompressed)

                    case 'application/x-xz':
                        tree = False
                        with lzma.open(file_bytes, 'rb') as f:
                            decompressed = f.read()
                            content = io.BytesIO(decompressed)

                    case 'application/x-7z-compressed':
                        ref =  py7zr.SevenZipFile(file_bytes, mode = 'r')
                        try:
                            extracted_paths = ref.getnames()
                            tree = True

                        except py7zr.exceptions.PasswordRequired:
                            encrypted = True

                    case 'application/vnd.rar' | 'application/x-rar':
                        with rarfile.RarFile(file_bytes) as rar:
                            rarfile.UNRAR_TOOL = "unrar"
                            tree = True
                            if not rar.needs_password():
                                extracted_paths = [info.filename for info in rar.infolist() if not info.isdir()]
                            else:
                                encrypted = True
                    case _:
                        raise Exception(f"Unsupported MIME type: {mime_type}")
                        tree = True

            except Exception as e:
                extracted_paths = [f"error:{str(e)}"]
            
            if not encrypted:
                if tree == True:
                    file_tree = flatten_tree(build_tree(extracted_paths))
                    request.session['file_tree'] = file_tree

                    file_bytes.seek(0)
                    encoded_file = base64.b64encode(file_bytes.read()).decode('utf-8')
                    request.session['uploaded_file_name'] = uploaded_file.name
                    request.session['uploaded_file_content'] = encoded_file

                    return redirect('tree')
                else:
                    request.session['uploaded_file_name'] = uploaded_file.name
                    
                    content.seek(0)
                    encoded_file = base64.b64encode(content.read()).decode('utf-8')
                    request.session['uploaded_file_content'] = encoded_file

                    return redirect('single-file')
            else:
                encoded_file = base64.b64encode(file_bytes.read()).decode('utf-8')
                request.session['uploaded_file_name'] = uploaded_file.name
                request.session['uploaded_file_content'] = encoded_file
    else:
        form = Upload
    return render(request, 'upload.html', {'form': form, 'meta_desc': 'Extract ZIP, RAR, 7Z, GZ, BZ2, and XZ archives online instantly. Our free archive extractor tool supports all popular formats for quick and easy file extraction on any device.'})

@csrf_exempt
def EnterPassword(request):
    msg = None

    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            encoded_file = request.session.get('uploaded_file_content')
            file_name = request.session.get('uploaded_file_name')

            if not encoded_file or not file_name:
                msg = "Session data missing. Please re-upload the file."
                return render(request, "enter_password.html", {"form": form, "msg": msg})

            file_bytes = io.BytesIO(base64.b64decode(encoded_file.encode('utf-8')))
            file_bytes.seek(0)
            extracted_paths = []
            tree = False
            mime_type = detect_mime(file_bytes)

            try:
                match mime_type:
                    case 'application/zip' | 'application/x-zip-compressed':
                        with zipfile.ZipFile(file_bytes) as zf:
                            file_to_test = zf.namelist()[0]
                            with zf.open(file_to_test, pwd=password.encode()) as f:
                                f.read(1)
                            extracted_paths = zf.namelist()
                            tree = True

                    case 'application/x-7z-compressed':
                        with py7zr.SevenZipFile(file_bytes, mode='r', password=password) as archive:
                            extracted_paths = archive.getnames()
                            tree = True

                    case 'application/vnd.rar' | 'application/x-rar':
                        rarfile.UNRAR_TOOL = "unrar"
                        with rarfile.RarFile(file_bytes) as rf:
                            file_to_test = rf.namelist()[0]
                            with rf.open(file_to_test, pwd=password) as f:
                                f.read(1)
                            extracted_paths = rf.namelist()
                            tree = True

                    case _:
                        msg = "Unsupported encrypted archive format."
                        return render(request, "enter_password.html", {"form": form, "msg": msg})

            except zipfile.BadZipFile:
                msg = "Invalid ZIP file or it is corrupt."
            except RuntimeError as e:
                msg = "Incorrect password for ZIP archive."
            except py7zr.exceptions.IncorrectPassword:
                msg = "Incorrect password for 7Z archive."
            except rarfile.BadPassword:
                msg = "Incorrect password for RAR archive."
            except Exception as e:
                msg = f"Decryption failed: {str(e)}"

            if msg:
                return render(request, "enter_password.html", {"form": form, "msg": msg})

            file_tree = flatten_tree(build_tree(extracted_paths))
            request.session['file_tree'] = file_tree
            request.session['uploaded_file_content'] = base64.b64encode(file_bytes.getvalue()).decode('utf-8')

            return redirect('tree')
    else:
        form = PasswordForm()

    return render(request, "enter_password.html", {"form": form, "msg": msg})

def Tree(request):
    file_tree = request.session.get('file_tree')
    file_name = request.session.get('uploaded_file_name')

    if not file_tree:
        return HttpResponse("No file tree found in session. Please upload first.")

    context = {
        'tree': file_tree,
        'name': file_name
    }

    return render(request, "tree.html", context)

def SingleFile(request):
    file = request.session.get('uploaded_file_content')
    file_name = request.session.get('uploaded_file_name')

    name = ''
    base_name, ext = os.path.splitext(file_name)
    name = base_name + "_decompressed"
    if not file:
        return HttpResponse("No file found in session. Please upload first.")
    
    context = {
        'name': name,
    }
    return render(request, "single-file.html", context)

def Download(request):
    encoded_file = request.session.get('uploaded_file_content')
    file_name = request.session.get('uploaded_file_name')

    if not encoded_file:
        return HttpResponse("No file found in session. Please upload first.")

    name = os.path.splitext(file_name)[0]

    file_content = base64.b64decode(encoded_file.encode('utf-8'))
    file = io.BytesIO(file_content)
    file.seek(0)
    response = FileResponse(file, as_attachment=True, filename=name)
    return response


def DownloadZip(request):
    file_string = request.session.get('uploaded_file_content')
    original_file_name = request.session.get('uploaded_file_name')

    if not file_string or not original_file_name:
        return HttpResponse("No uploaded file to download.", status=404)


    file_content = base64.b64decode(file_string.encode('utf-8'))
    file_bytes = io.BytesIO(file_content)
    file_bytes.seek(0)
    mime_type = detect_mime(file_bytes)

    zip_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as new_zip:
            match mime_type:
                case 'application/zip' | 'application/x-zip-compressed':
                    with zipfile.ZipFile(io.BytesIO(file_content), 'r') as original_zip:
                        for member_name in original_zip.namelist():
                            data = original_zip.read(member_name)
                            new_zip.writestr(member_name, data)

                case 'application/x-tar' | 'application/gzip' if original_file_name.endswith('.tar.gz'):
                    with tarfile.open(fileobj=io.BytesIO(file_content), mode='r:*') as original_tar:
                        for member in original_tar.getmembers():
                            if member.isfile():
                                f = original_tar.extractfile(member)
                                if f:
                                    data = f.read()
                                    new_zip.writestr(member.name, data)

                case 'application/x-7z-compressed':
                    archive = py7zr.SevenZipFile(io.BytesIO(file_content))
                    
                    with tempfile.TemporaryDirectory() as dir:
                        extract = archive.extractall(path = dir)
                        for root, _, files in os.walk(dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, dir)
                                new_zip.write(file_path, arcname=arcname)

                case 'application/vnd.rar' | 'application/x-rar':
                    with rarfile.RarFile(io.BytesIO(file_content)) as rar:
                        rarfile.UNRAR_TOOL = "unrar"
                        for info in rar.infolist():
                            if not info.isdir():
                                data = rar.read(info)
                                new_zip.writestr(info.filename, data)

                case _:
                    new_zip.writestr(original_file_name, file_content)

    except Exception as e:
        return HttpResponse(f"Error processing archive: {str(e)}", status=500)

    zip_buffer.seek(0)
    base_name = os.path.splitext(original_file_name)[0]
    download_file_name = f"{base_name}.zip"
    response = FileResponse(zip_buffer, as_attachment=True, filename=download_file_name)
    response['Content-Type'] = 'application/zip'
    return response

