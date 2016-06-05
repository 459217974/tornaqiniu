#-*- coding:utf-8 -*-
from tornado import gen,httpclient
import hmac
import hashlib
import base64
from datetime import datetime
from .errors import *
from .utils import *
from . import PUT_POLICY
from .common import Auth,QiniuResourceOperationBase


##################################################################
#
# Qiniu Resource Loader that's responsible for uploading resource to
# bucket or downloading resource from bucket and generate download url
#
#
#################################################################

class QiniuResourceLoader(QiniuResourceOperationBase):
	def __init__(self,bucket,auth):
		super(QiniuResourceLoader,self).__init__(bucket,auth)
		self._policys={}
	def _check_policy(self,field,value):
		if policy_field not in PUT_POLICY.keys():
				raise PolicyKeyError("Not support '%s' policy"%policy_field)		
		if not isinstance(policy_value,PUT_POLICY[policy_field]['type']):
				raise PolicyValueTypeError("Policy '%s' value type error"%policy_field)
	def add_policy(self,policy_field,policy_value):
		self._check_policy(policy_field,policy_value)
		self._policys[policy_field]=policy_value
	def add_policys(self,policy_pairs):
		for key,value in policy_pairs.items():
			self._check_policy(key,value)
			self._policys[key]=value
	def delete_policy(self,field):
		if field in self._policys:
			del self._policys[field]
	def delete_policys(self,fields):
		for field in fields:
			self.delete_policy(field)
	def delete_all_policys(self):
		del self._policys
		self._policys={}
	def modify_policy(self,field,value):
		self._policys[field]=value
	@property
	def policys(self):
		return self._policys
	def get_policys(self):
		return self._policys
	def get_flush_policys(self):
		policys=self._policys
		self._policys={}
		return policys
	def _gen_private_url(self,key,host,expires=3600):
		assert host!=None and host!="","download host can' be empty"
		if not host.startswith("http://"):
			host="http://"+host
		download_url=host+'/'+key
		token=self._auth.download_token(download_url,expires=expires)
		download_url+='?e='+str(int(datetime.timestamp(datetime.now()))+expires)
		download_url+="&token="+token
		return download_url
	def private_url(self,key,host,expires=3600):
		r"""
			generate one private url 
			
			@parameters:
				key:resource key,'str' type,
				expires:'int' type,units:'s',
				host:resource host name
		"""
		return self._gen_private_url(key,expires,host)
	def private_urls(self,keys,host,expires=3600,key_name=None):
		"""
			generate multi private urls at the same time
		
			@parameters
				keys:resource keys ,'list','dict' or  'tuple' type,
				expires:int type,units:'s',
				host:resource host name,
				key_name:when  'keys' type  is 'dict',your must point out key name in 'keys'
			@return:
				download_urls: 'list' typw
		"""
		download_urls=[]
		if isinstance(keys,(list,tuple)):
			if key_name:
				for key in keys:
					download_urls.append(self._gen_private_url(key[key_name]),expires,host)
			else:
				for key in keys:
					download_urls.append(self._gen_private_url(key,expires,host))
		else:
			pass
		return download_urls
	def _gen_public_url(self,key,host):
		assert host!=None and host!=""," host can't be empty"
		if not host.startswith("http://"):
			host="http://"+host
		download_url=host+'/'+key
		return download_url
	def public_url(self,key,host):
		r"""
			generate public url 
			
			@parameters:
				key:resource key,'str' type,
				host:resource host name
		"""
		return self._gen_public_url(key,host)
	def public_urls(self,keys,host,key_name=None):
		r"""
			generate multi public url
			the parameters difinition is same with 'private_urls'
		"""
		download_urls=[]
		if isinstance(keys,(tuple,list)):
			if key_name:
				for key in keys:
					download_urls.append(self._gen_public_url(key[key_name],host))
			else:
				for key in keys:
					download_urls.append(self._gen_public_url(key,host))
		else:
			pass
		return download_urls	
	
	
class _Batch(object):
	def __init__(self,client):
		self.__client=client
		self.__operations=[]
	@gen.coroutine
	def execute(self):
		pass
	def __setattr__(self,attr,value):
		pass
################################################################################
#
#
#Qiniu Resource manager that's responsible for bucket resouce management ,
#like 'delete','copy','move' and so on
#
#
#
##############################################################################
class QiniuResourceManager(QiniuResourceOperationBase):
	def __init__(self,bucket,auth):
		super(QiniuResourceManager,self).__init__(bucket,auth)
	@gen.coroutine
	def _send_manage_request(self,url_path,host="rs.qiniu.com",body=None,method=None):
		full_host="http://"+host
		url=full_host+url_path
		headers={
			"Authorization":self._auth.callback_verify_header(url_path,body),
			"Host":host
		}
		response=yield self.send_async_request(url,headers=headers,method=method or "GET",body=body)
		return response
	@gen.coroutine
	def stat(self,key,bucket=None):
		bucket=bucket or self._bucket
		entry=bucket+":"+key
		encoded_entry=bytes_decode(urlsafe_base64_encode(entry))
		response= yield self._send_manage_request("/stat/"+encoded_entry)
		return response
	@gen.coroutine
	def move(self,src_bucket,src_key,dest_bucket,dest_key):
		src_entry=bytes_decode(urlsafe_base64_encode(src_bucket+':'+src_key))
		dest_entry=bytes_decode(urlsafe_base64_encode(dest_bucket+':'+dest_key))
		response=yield self._send_manage_request("/move/"+src_entry+'/'+dest_entry,method="POST")
		return response
	@gen.coroutine
	def modify_mime(self,bucket,key,mine_type):
		pass

	@gen.coroutine
	def copy(self,src_bucket,src_key,dest_bucket,dest_key):
		src_encoded_entry=bytes_decode(urlsafe_base64_encode(src_bucket+":"+src_key))
		dest_encoded_entry=bytes_decode(urlsafe_base64_encode(dest_bucket+":"+dest_key))
		response=yield self._send_manage_request("/copy/"+src_encoded_entry+"/"+dest_encoded_entry,method="POST")
		return response
	@gen.coroutine
	def delete(self,key,bucket=None):
		bucket=bucket or self._bucket
		encoded_entry=bytes_decode(urlsafe_base64_encode(bucket+":"+key))
		response =yield self._send_manage_request("/delete/"+encoded_entry,method="POST")
		return response
	@gen.coroutine
	def list(self,bucket=None,limit=1000,prefix="",delimiter="",marker=""):
		bucket=bucket or self._bucket
		assert limit>1 and limit<=1000,"limit must bettween 1 to 1000"
		query_string=urlencode({
			'bucket':bucket,
			'limit':limit,
			'marker':marker,
			'prefix':prefix,
			'delimiter':delimiter,
		})	
		response=yield self._send_manage_request('/list?'+query_string,host="rsf.qbox.me",method="POST")
		return response
	@gen.coroutine
	def fetch_store(self,fecth_url,key=None,bucket=None):
		bucket=bucket or self._bucket
		if key:
			encoded_entry=bytes_decode(urlsafe_base64_encode(bucket+":"+key))
		else:
			encode_entry=bytes_decode(urlsafe_base64_encode(bucket))
		encoded_fecth_url=bytes_decode(urlsafe_base64_encode(fetch_url))
		response=yield self._send_manage_request('/fetch/'+encoded_fetch_url+'/to/'+encoded_entry,host='iovip.qbox.me',method="POST")
		return response
	@gen.coroutine
	def batch(self,*opers):
		opertions={}
		for oper in opers:
			opertions['op']=oper
		opertions_body=urlencode(opertions)
		response=yield self._send_manage_request('/batch',method="POST",body=opertions_body)
		return response
	@gen.coroutine
	def prefecth(self,key,bucket=None):
		bucket=bucket or self._bucket
		encoded_entry=bytes_decode(urlsafe_base64_encode(bucket+':'+key))
		response=yield self._send_manage_request('/prefecth/'+encoded_entry,method="POST",host="iovip.qbox.me")
		return response
	
		
################################################################################
#
#
#Qiniu resource processor that's responsible for bucket resource procession 
#like 'imageView2','QRCode','Audio/Vedio thumb'
#		
#################################################################################
class _QiniuResourceOpsInterface(object):
	"""
		this class defines all qiniu resource prosession interface 
	"""
	_gravity_map={1:"NorthWest",2:"North",3:"NorthEast",
		     4:"West",5:"Center",6:"East",
		     7:"SouthWest",8:"South",9:"SouthEast"}
	def image_watermark_interface(self,
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
	
	def text_watermark_interface(self,
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

	def image_view2_interface(self,mode,width=None,height=None,frmt=None,interlace=0,quality=75,ignore_error=0):
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
		interface="imageView2/"+str(mode)
		if width:
			interface='/w/'+str(width)
		if height:
			interface='/h/'+str(width)
		if frmt:
			interface='/format/'+str(frmt)
		if interlace!=0:
			interface='/interlace/'+str(interlace)
		if quality!=75:
			interface='/quality/'+str(quality)
		if ignore_error!=0:
			interface+='/ignore-error/'+str(ignore_error)
		return interface

	def qrcode_interface(self,mode,level):
		_level_map={1:"L",2:"M",3:"Q",4:"H"}
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
		interface="qrcode/"+str(mode)+'/level/'+str(_level_map.get(level))
		return interface
	def avthumb_transcoding_interface(self,frmt,**options):
		"""
			The  'options' parameter  detail definition refers to :
				 http://developer.qiniu.com/code/v6/api/dora-api/av/avthumb.html
		"""
		interface="avthumb/%s"%str(frmt)
		if len(options)>0:
			interface+=self._options_dict_to_str(options)
		return interface
	def _options_dict_to_str(self,options):
		options_list=list(options.items())
		options_list=list(map(lambda item:"/"+str(item[0])+"/"+str(item[1]),options_list))
		options_str=reduce(lambda op1,op2:op1+op2,options_list)
		return options_str
	def avthumb_slice_interface(self,no_domain,**options):
		"""
			'options' detail definition refer to:
				http://developer.qiniu.com/code/v6/api/dora-api/av/segtime.html
		"""
		if int(no_domain)>0:
			no_domain=1
		else:
			no_domain=0
		interface="avthumb/m3u8/noDomain/%s"%str(no_domain)
		if len(options)>0:
			interface+=self._options_dict_to_str(options)
		return interface
	def avconcat_interface(self,mode,frmt,*encoded_urls):
		"""
			detail refer to:
				http://developer.qiniu.com/code/v6/api/dora-api/av/avconcat.html
		"""
		interface="avconcat/"+str(mode)+'/format/'+str(frmt)
		for encoded_url in encoded_urls:
			interface+='/'+encoded_url
		return interface
	def vframe_interface(self,out_img_frmt,offset,width=None,heigth=None,rotate=None):
		"""
			detail definition refer to:
				http://developer.qiniu.com/code/v6/api/dora-api/av/vframe.html
		"""
		interface='vframe/'+str(out_img_frmt)+'/offset/'+str(offset)
		if width:
			assert width>=1 and width<=3840
			interface+='/w/'+str(width)
		if heigth:
			assert heigth>=1 and height<=2160
			interface+='/h/'+str(height)
		if rotate:
			assert rotate in [90,180,270,'auto']
			interface+='/rotate/'+str(rotate)
		return interface
	def vsample_interface(self,out_img_frmt,
			     start_second,
			     sample_time,
			     resolution_width=None,
		             resolution_height=None,
			     rotate=None,
			     sample_interval=None,
			     pattern=None):
		"""
			detail definition refer to:
				http://developer.qiniu.com/code/v6/api/dora-api/av/vsample.html
		"""
		interface="vsample/"+str(out_img_frmt)+'/ss/'+str(start_second)
		interface+='/t/'+str(sample_time)
		if resolution_width and resolution_height:
			assert resolution_width>=1 and resolution_width<=1920
			assert resolution_height>=1 and resolution_height<=1080
			interface+='/s/'+str(resolution_width)+'x'+str(resolution_height)
		if rotate:
			assert rotate in (90,180,270,'auto')
			interface+='/rotate/'+str(rotate)
		if sample_interval:
			interface+='/interval/'+str(sample_intervale)
		if pattern:
			interface+=bytes_decode(urlsafe_base64_encode(pattern))
		return 	interface
	

	

class QiniuImageProcessMixin:
	def image_view2(self,url,mode,width=None,height=None,frmt=None,interlace=0,quality=75,ignore_error=0):
		interface=self.image_view2_interface(mode,width,height,frmt,interlace,quality,ignore_error)
		resulted_url=url
		if url.find("?")>=0:
			resulted_url+="&"+interface
		else:
			resulted_url+="?"+interface
		return resulted_url
	def image_watermark(self,origin_url,water_image_url,dissolve=100,gravity=9,dx=10,dy=10,ws=0):
		watermark_interface=self.image_watermark_interface(water_image_url,dissolve,gravity,dx,dy,ws)
		resulted_url=origin_url
		if origin_url.find("?")>=0:
			resulted_url+='&'+watermark_interface
		else:
			resulted_url+='?'+watermark_interface
		return resulted_url	

	def text_watermark(self,origin_url,text,font="宋体",font_size=500,fill="#000",dissolve=100,gravity=9,dx=10,dy=10):
		watermark_interface=self.text_watermark_interface(text,font,font_size,fill,dissolve,gravity,dx,dy)
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
		response=yield self.send_async_request(url)
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
		response=yield self.send_async_request(url)
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
		response=yield self.send_async_request(url)
		if response:
			return json_decode(response).get("RGB")

class QiniuAVProcessMixin:
	def avinfo_url(self,av_url):
		if av_url.find("?")>=0:
			return av_url+"&avinfo"
		else:
			return av_url+"?avinfo"
	@gen.coroutine
	def get_avinfo(self,av_url):
		avinfo_url=self.avinfo_url(av_url)
		response=yield self.send_async_request(avinfo_url)
		if response:
			return json_decode(response)
		return None
	

class _PersistentWrapper(object):
	"""
		make persistent operation 'pipeline' like executing
	"""
	def __init__(self,client_obj,key,fops,notify_url,bucket,force,pipeline):
		self.__client=client_obj
		self.__key=key
		self.__fops=[]
		self.__fops.extend(fops or "")
		self.__notify_url=notify_url
		self.__bucket=bucket or self.__client._bucket
		self.__force=force
		self.__pipeline=pipeline
	@gen.coroutine
	def execute(self):
		assert self.__bucket,"bucket can't be none"
		assert len(self.__fops)>0,"fops can't be none"
		self.__fops=reduce(lambda op1,op2:str(op1)+';'+str(op2),self.__fops)		
		body=urlencode({
			'bucket':self.__bucket,
			'key':self.__key,
			'fops':self.__fops,
			'notifyURL':self.__notify_url,
			'pipeline':self.__pipeline or "",
			'force':self.__force
		})	
		response=yield 	self.__client._send_persistent_request('/pfop/',body=body,method="POST")
		if response:
			return json_decode(response)
		return None
	def add_fops(self,ops):
		self.__fops.append(ops)	
	def add_multi_fops(self,ops_list):
		self.__fops.extend(list(ops_lsit))
	def set_pipeline(self,pipeline):
		self.__pipeline=pipeline
	def set_notify_url(self,url):
		self.__notify_url=url
	def set_force(self,force):
		if int(force)>0:
			self.__force=1
		else:
			self.__force=0
	def set_key(self,key):
		self.__key=key
	def set_bucket(self,bucket):
		self.__bucket=bucket
	

class QiniuResourceProcessor(QiniuResourceOperationBase,
                           QiniuAVProcessMixin,
			   QiniuImageProcessMixin,
			   _QiniuResourceOpsInterface):
	def __init__(self,bucket,auth):	
		super(QiniuResourceProcessor,self).__init__(bucket,auth)
	def qrcode_url(self,url,mode=0,level=1):
		resulted_url=url
		interface=self.qrcode_interface(mode,level)
		if url.find("?")>=0:
			resulted_url+='&'+interface
		else:
			resulted_url+='?'+interface
		return resulted_url
			
	@gen.coroutine
	def _send_persistent_request(self,url_path,host="api.qiniu.com",body=None,method=None):
		url="http://"+host+url_path
		headers={}
		headers['Authorization']=self._authorization(url_path,body)
		headers['Host']=host
		response=yield self.send_async_request(url,headers=headers,method=method or "POST",body=body)
		return response	
	def persistent(self,key,notify_url,fops=None,bucket=None,force=1,pipeline=None):
		""" 
			Usage:
			
				client=QiniuClient('access_key','secret_key',bucket='your bucket')
				persistent.add_fops(client.text_watermark_interface("hello"))
				yield persistent.execute()
			
				
		"""
		return _PersistentWrapper(self,key,fops,notify_url,bucket,force,pipeline)
	@gen.coroutine
	def prefop(self,persistent_id):
		url_path="/status/get/prefop?id=%s"%str(persistent_id)
		response=yield self._send_persistent_request(url_path,method="GET")	
		if response:
			return json_decode(response)
		
################################################################################
#
#
#Qiniu bucket resource map class
#
#
#
###############################################################################
class Resource(object):
	r"""
		A map class  to qiniu bucket resource
	"""
	def __init__(self,key,bucket):
		r"""
		Args:
			key:resource key name,
			bucket:bucket object,
		"""
		self.__key=key
		self.__bucket=bucket
	def url(self,*args,**kwargs):
		pass
