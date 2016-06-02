#-*- coding:utf-8 -*-
from tornado import gen,httpclient
from tornado.httpclient import AsyncHTTPClient
import json
from .resource_manage import QiniuResourseManageMixin
from .resource_load import QiniuResourceLoadMixin
from .resource_process import QiniuImageProcessMixin,QiniuResourceQRCodeMixin
from .errors import EncodingError
import base64
import hmac
class QiniuClient(
		QiniuResourseManageMixin,
		QiniuResourceLoadMixin,
		QiniuImageProcessMixin,
		QiniuResourceQRCodeMixin	
		):
	def __init__(self,access_key,secret_key,download_host=None,bucket=None):
		assert isinstance(access_key,(str,bytes))
		assert isinstance(secret_key,(str,bytes))
		assert isinstance(bucket,(type(None),str,bytes))
		self._access_key=access_key
		self._secret_key=secret_key
		self._bucket=bucket
		self._download_host=download_host
		self._policys={}
	def _urlsafe_base64_encode(self,policy):
		if isinstance(policy,str):
			return base64.urlsafe_b64encode(self._bytes_encode(policy))
		elif isinstance(policy,bytes):
			return base64.urlsafe_b64encode(policy)
		else:
			raise EncodingError("'policy' must be str or bytes type")
	def _json_encode(self,need_encode):
			return json.dumps(need_encode)
	def _json_decode(self,need_decode):
			return json.loads(need_decode)
	def _bytes_encode(self,need_encode):
			return need_encode.encode("utf-8")
	def _bytes_decode(self,need_decode):
			return need_decode.decode("utf-8")		
	def _hmac_sha1(self,key,data):
		if isinstance(key,str):
			key=self._bytes_encode(key)
		elif not isinstance(key,bytes):
			raise EncodingError("'key' must be 'str' or 'bytes' type")
		else:
			pass
		if isinstance(data,str):
			data=self._bytes_encode(data)
		elif not isinstance(data,bytes):
			raise EncodingError("'data' must be 'str' or 'bytes' type")
		else:
			pass
		return hmac.new(key,data,'sha1').digest()
	@gen.coroutine
	def _send_async_request(self,url,method="GET",body=None):
		headers={}
		if body or method.upper()=="POST":
			headers['Content-Type']="application/x-www-form-urlencoded"
		req=httpclient.HTTPRequest(url,method=method,body=body,headers=headers,allow_nonstandard_methods=True)
		http_request=AsyncHTTPClient()
		try:
			response=yield http_request.fetch(req)
		except httpclient.HTTPError as e:
			print("Error:"+str(e))
		else:
			return response.body.decode()
		finally:
			http_request.close()




