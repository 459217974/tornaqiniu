#-*- coding:utf-8 -*-
from tornado import gen,httpclient
import hmac
import base64
import urllib
from .utils import *

class QiniuImageProcessMixin(object):
	_gravity_map={1:"NorthWest",2:"North",3:"NorthEast",
		     4:"West",5:"Center",6:"East",
		     7:"SouthWest",8:"South",9:"SouthEast"}
	def image_view2(self,url,mode,width=None,height=None,frmt=None,interlace=0,quality=75,ignore_error=0):
		r"""
			qiniu imageView2 procession
			
			@parameters:
				'url':image url,
				'mode':image procession mode,the specific definition as follows:
					1.mode 0:
						image's long edge max is 'width',image's short edge max is 'height' and 
						don't perform cut opertion.If just specific 'witdh' or 'height' ,
						then another edge will be self-adjust.
					2.mode 1:
						images' min width is 'width' and min heigth is 'height'.
						performing middle cut opertion.If just specific 'width' or 'height',
						then width will be equal to height
					3.mode 2:
						this mode almost be same with mode 0,the only difference is mode 2 
						limit images' width and height.mode 0 is suitable for mobile ,
						mode 2 is suitable for PC
					4.mode 3:
						image's  min width is 'width' and min height is 'height',
						don't perform cut opertions.If just specific 'width' or 'height',
						then widht will be equal to height
					5.mode 4:
						..............
					6.mode 5:	
						.............
				'width':image processed width,
				'height':image processed height,
				'frmat':image format,supporting .jpg,.gif,.png,.webp,
				'interlace':image interlace show,the default values is true
				'quality':image processed quality,range from 0 to 100,the default value is 75,
				'ignore-error':whether to ignore error,when image procession failed!.the default value is true
		"""
		assert mode<6 and mode>=0,"'mode' must range from 0 to 5"
		assert width or height,"both 'width' and 'height' can't be none "
		assert quality<=100 and quality>=0,"'quality' must range from 0 to 100"
		p_pattern=""
		p_pattern+="imageView2/"+str(mode)
		if width:
			p_pattern+='/w/'+str(width)
		if height:
			p_pattern+='/h/'+str(width)
		if frmt:
			p_pattern+='/format/'+str(frmt)
		if interlace!=0:
			p_pattern+='/interlace/'+str(interlace)
		if quality!=75:
			p_pattern+='/quality/'+str(quality)
		if ignore_error!=0:
			p_pattern+='/ignore-error/'+str(ignore_error)
		if url.find("?")>=0:
			url+="&"+p_pattern
		else:
			url+="?"+p_pattern
		return url
	def _image_watermark_interface(self,
			   water_image_url,
			   dissolve=100,
			   gravity=9,
			   dx=10,
			   dy=10,
			   ws=0):
		r"""
			The detail definition of parameters,please refer to qiniu documents
		"""
		assert isinstance(dissolve,int) and dissolve>=1 and dissolve<=100
		assert isinstance(gravity,int) 
		assert isinstance(dx,int) and isinstance(dy,int)
		assert float(ws)>=0.0 and float(ws)<=1.0
		interface="watermark/1"
		interface+='/image/'+str(bytes_decode(urlsafe_base64_encode(water_image_url)))
		interface+='/dissolve/'+str(dissolve)
		interface+='/gravity/'+str(self._gravity_map.get(gravity,"SouthEast"))
		interface+='/dx/'+str(dx)
		interface+='/dy/'+str(dy)
		interface+='/ws/'+str(ws)
		return interface
	def image_watermark(self,origin_url,water_image_url,dissolve=100,gravity=9,dx=10,dy=10,ws=0):
		watermark_interface=self._image_watermark_interface(water_image_url,dissolve,gravity,dx,dy,ws)
		resulted_url=origin_url
		if origin_url.find("?")>=0:
			resulted_url+='&'+watermark_interface
		else:
			resulted_url+='?'+watermark_interface
		return resulted_url	
	def _text_watermark_interface(self,
				text,
				font="宋体",
				font_size=500,
				fill="#ffffff",
				dissolve=100,
				gravity=9,
				dx=10,
				dy=10):
		r"""
			The detail  definition of parameters,please refer to qiniu documents
		"""
		assert isinstance(font,str)
		assert isinstance(font_size,int)
		assert isinstance(fill,str)
		assert isinstance(dissolve,int) and dissolve>=1 and dissolve<=100
		assert isinstance(gravity,int)
		assert isinstance(dx,int) and isinstance(dy,int)
		interface="watermark/2"
		interface+='/text/'+str(bytes_decode(urlsafe_base64_encode(text)))
		interface+='/font/'+str(bytes_decode(urlsafe_base64_encode(font)))
		interface+='/fontsize/'+str(font_size)
		interface+='/fill/'+str(bytes_decode(urlsafe_base64_encode(fill)))
		interface+='/dissolve/'+str(dissolve)
		interface+='/gravity/'+str(self._gravity_map.get(gravity,"SouthEast"))
		interface+='/dx/'+str(dx)
		interface+='/dy/'+str(dy)
		return interface

	def text_watermark(self,origin_url,text,font="宋体",font_size=500,fill="#000",dissolve=100,gravity=9,dx=10,dy=10):
		watermark_interface=self._text_watermark_interface(text,font,font_size,fill,dissolve,gravity,dx,dy)
		resulted_url=origin_url
		if origin_url.find("?")>=0:
			resulted_url+='&'+watermark_interface
		else:
			resulted_url+="?"+watermark_interface
		return resulted_url
	def multi_watermark(self,origin_url,*args):
		"""
			multi watermark parameters are too much,
			so i decided to implement it at the next time.
		"""
		pass
	def imageinfo_url(self,origin_url):
		if origin_url.find("?")>=0:
			return origin_url+"&imageInfo"
		else:
			return origin_url+"?imageInfo"
	def multi_imageinfo_url(self,urls,key_name=None):
		if isinstance(urls,(list,tuple)):
			info_urls=[]
			if key_name:
				# for 'list' or 'tuple' like this:[{"key1":"xx","key2":"21"},{..},{..},...]
				for url in urls:
					info_urls.append(self.imageinfo_url(url[key_name]))
			else:
				# for 'list' or 'tuple'  like this: [url1,url2,....]
				for url in urls:
					info_urls.append(self.imageinfo_url(url))
			return info_urls
		return None
	@gen.coroutine
	def get_imageinfo(self,origin_url):
		url=self.imageinfo_url(origin_url)
		response=yield self._send_async_request(url)
		if response:
			return json_decode(response)
	def imageexif_url(self,origin_url):
		if origin_url.find("?")>=0:
			return origin_url+'&exif'
		else:
			return origin_url+'?exif'
	def multi_imageexif_url(self,urls,key_name=None):
		if isinstance(urls,(list,tuple)):
			exif_urls=[]
			if key_name:
				for url in urls:
					exif_urls.append(self.imageexif_url(url[key_name]))
			else:
				for url in urls:
					exif_urls.append(self.imageexif_url(url))
			return exif_urls
	@gen.coroutine
	def get_imageexif(self,origin_url):
		url=self.imageexif_url(origin_url)
		response=yield self._send_async_request(url)
		return response							
	def imageave_url(self,origin_url):
		if origin_url.find("?")>=0:
			return origin_url+'&imageAve'
		else:
			return origin_url+'?imageAve'
	def multi_imageave_url(self,urls,key_name):
		if  isinstance(urls,(list,tuple)):
			ave_urls=[]
			if key_name:
				for url in urls:
					ave_urls.append(self.imageave_url(url[key_name]))
			else:
				for url in urls:
					ave_urls.append(self.iamgeave_url(url))
			return ave_urls
	@gen.coroutine
	def get_imageave(self,origin_url):
		url=self.imageave_url(origin_url)
		response=yield self._send_async_request(url)
		if response:
			return json_decode(response).get("RGB")

class QiniuResourceQRCodeMixin(object):	
	_level_map={1:"L",2:"M",3:"Q",4:"H"}
	def _qrcode_interface(self,mode,level):
		r"""
			generate QR code for resource 
			
			@parameter:
				1.download_url:resource download url,
				2.mode: 0 or 1,
				3.level: QR code image size,the value
				range from 1 to 4
		"""
		assert int(mode)==0 or int(mode)==1,"'mode' must be 0 or 1"
		assert int(level) in [1,2,3,4],"'level' must range from 1 to 4"
		interface="qrcode/"+str(mode)+'/level/'+str(self._level_map.get(level))
		return interface
	def qr_code(self,url,mode=0,level=1):
		resulted_url=url
		interface=self._qrcode_interface(mode,level)
		if url.find("?")>=0:
			resulted_url+='&'+interface
		else:
			resulted_url+='?'+interface
		return resulted_url



class QiniuResourceMDToHTMLMixin(object):
	"""
		convert mardown to html
		@parameters:
			1.mode:0 or 1
			2.css: url of css style
	"""
	def _md2html_url(self,url,mode,css):
		assert int(mode)==0 or int(mode)==1,"'mode' must be 0 or 1"
		interface="md2html/"+str(mode)+'/css/'+bytes_decode(urlsafe_base64_encode(css))
		resulted_url=url
		if resulted_url.find("?")>=0:
			resulted_url+="?"+interface
		else:
			resulted_url+='&'+interface
		return resulted_url
	
class QiniuResourcePersistentMixin(object):
	@gen.coroutine
	def _send_persistent_request(self,url_path,host="api.qiniu.com",body=None,method=None):
		url="http://"+host+url_path
		headers={}
		headers['Authorization']=self._authorization(url_path,body)
		headers['Host']=host
		response=yield self._send_async_request(url,headers=headers,method=method or "POST",body=body)
		return response	
	@gen.coroutine
	def persistent(self,key,fops,notify_url,bucket=None,force=1,pipeline=None):
		bucket=bucket or self._bucket
		assert bucket,"bucket can't be none"
		body=urlencode({
			'bucket':bucket,
			'key':key,
			'fops':fops,
			'notifyURL':notify_url,
			'pipeline':pipeline or "",
			'force':force
		})
		response=yield self._send_persistent_request('/pfop/',body=body)
		return response
		

			
