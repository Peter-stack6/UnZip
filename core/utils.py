import magic

def manual_mime(file):
	base = "application"
	ext_map = {
		'.zip': f"{base}/zip",
		'.tar': f"{base}/x-tar",
		'.gz': f"{base}/gzip",
		'.7z': f"{base}/x-7z-compressed",
		'.rar': f"{base}/x-rar-compressed"
	}
	for ext, mime in ext_map.items():
		if file.name.endswith(ext):
			return mime

def detect_mime(file):
    mime = magic.Magic(mime=True)
    
    file.seek(0)
    mime_type = mime.from_buffer(file.read(2048))
    file.seek(0)
    
    return mime_type