#-*- coding:utf-8 -*_
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
import base64
import hmac
import urllib
from urllib import request

class QiniuResourseManageMixin(object):
	def _encode_entry(self,entry):
		if isinstance(entry,bytes):
			return base64.urlsafe_b64encode(entry)
		if isinstance(entry,str):
			return base64.urlsafe_b64encode(entry.encode("utf-8"))
	def _access_token(self,url_path,body=None):
		signing_str=url_path+"\n"
		if body:
			signing_str=signing_str+body
		sign=hmac.new(self.__secret_key,signing_str,'sha1')
		encoded_sign=base64.urlsafe_b64encode(sign.digest)
		access_token=self.__access_key+":"+encoded_sign
		return access_token
	@gen.coroutine
	def _send_manage_request(self,url_path,host="rs.qiniu.com",body=None,method=None):
		full_host="http://"+host
		url=full_host+url_path
		req=request.Request(url,method=method,data=body)
		req.add_header("Authorization","QBox "+self._access_token(url_path,body))
		req.add_header("Host",host)
		if body or method=="POST":
			req.add_header("Content-Type","application/x-www-form-urlencoded")
		http_request=AsyncHTTPClient()
		try:
			response=yield http_request.fetch(req)
		except httpclient.HTTPError as e:
			print("Error:"+str(e))
		except Exception as e:
			print("Error:"+str(e))
		else:
			return response.body
		finally:	
			http_request.close()
	@gen.coroutine
	def stat(self,bucket,key):
		entry=bucket+":"+key
		encoded_entry=self._encode_entry(entry)
		response= yield self._send_manage_request("/stat/"+encoded_entry)
		return response
	@gen.coroutine
	def move(self,src_bucket,src_key,dest_bucket,dest_key):
		src_entry=self._encode_entry(src_bucket+':'+src_key)
		dest_entry=self._encode_entry(dest_bucket+':'+dest_key)
		response=yield self._send_manage_request("/move/"+src_entry+'/'+dest_entry,method="POST")
		return response
	@gen.coroutine
	def modify_mime(self,bucket,key,mine_type):
		pass

	@gen.coroutine
	def copy(self,src_bucket,src_key,dest_bucket,dest_key):
		src_encoded_entry=self._encode_entry(src_bucket+":"+src_key)
		dest_encoded_entry=self._encode_entry(dest_bucket+":"+dest_key)
		response=yield self._send_manage_request("/copy/"+src_encoded_entry+"/"+dest_encoded_entry,method="POST")
		return response
	@gen.coroutine
	def delete(self,bucket,key):
		encoded_entry=self._encode_entry(bucket+":"+key)
		response =yield self._send_manage_request("/delete/"+encoded_entry,method="POST")
		return response
	@gen.coroutine
	def list(self,bucket,limit=1000,prefix="",delimiter="",marker=""):
		assert limit>1 and limit<=1000,"limit must bettween 1 to 1000"
		query_string=urllib.parse.urlencode({
			'bucket':self._encode_entry(bucket),
			'limit':limit,
			'marker':marker,
			'prefix':self._encode_entry(prefix),
			'delimiter':self._encode_entry(prefix),
		})	
		response=yield self._send_manage_request('/list?'+query_string,host="rsf.qbox.me",method="POST")
		return response
	@gen.coroutine
	def fetch(self,fecth_url,bucket,key=None):
		if key:
			encoded_entry=self._encode_entry(bucket+":"+key)
		else:
			encode_entry=self._encode_entry(bucket)
		encoded_fecth_url=self._encode_entry(fetch_url)
		response=yield self._send_manage_request('/fetch/'+encoded_fetch_url+'/to/'+encoded_entry,host='iovip.qbox.me',method="POST")
		return response
	@gen.coroutine
	def batch(self,*opers):
		opertions={}
		for oper in opers:
			opertions['op']=oper
		opertions_body=urllib.parse.urlencode(opertions)
		response=yield self._send_manage_request('/batch',method="POST",body=opertions_body)
		return response
	@gen.coroutine
	def prefecth(self,bucket,key):
		encoded_entry=self._encode_entry(bucket+':'+key)
		response=yield self._send_manage_request('/prefecth/'+encoded_entry,method="POST",host="iovip.qbox.me")
		return response
	
		
		
		
