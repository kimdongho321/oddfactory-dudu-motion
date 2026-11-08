package com.oddfactory.dudu;
import android.content.Context;
import android.graphics.Color;
import android.net.Uri;
import android.webkit.*;
import java.io.*;
import java.util.*;
/** 앱 assets만 https://app.dudu.local/ 로 내보내는 투명 WebView(같은 출처라 캔버스 픽셀 읽기가 막히지 않음). */
final class RuntimeView extends WebView {
 static final String HOST="app.dudu.local";
 @android.annotation.SuppressLint({"JavascriptInterface","SetJavaScriptEnabled"})
 RuntimeView(Context context,Object bridge,Runnable loaded){super(context);setBackgroundColor(Color.TRANSPARENT);getSettings().setJavaScriptEnabled(true);getSettings().setAllowFileAccess(false);getSettings().setAllowContentAccess(false);getSettings().setDomStorageEnabled(false);getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS);setVerticalScrollBarEnabled(false);setHorizontalScrollBarEnabled(false);setOverScrollMode(OVER_SCROLL_NEVER);addJavascriptInterface(bridge,"AndroidPet");
 setWebViewClient(new WebViewClient(){
  public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return true;}
  public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest request){Uri u=request.getUrl();String p=u.getPath();if(!"https".equals(u.getScheme())||!HOST.equals(u.getHost())||p==null||p.contains("..")||p.contains("\\")||p.indexOf('\0')>=0)return response(403,"text/plain",new ByteArrayInputStream(new byte[0]));if(p.equals("/favicon.ico"))return response(204,"image/x-icon",new ByteArrayInputStream(new byte[0]));if(p.equals("/"))p="/screen.html";try{return response(200,mime(p),getContext().getAssets().open(p.substring(1)));}catch(IOException e){return response(404,"text/plain",new ByteArrayInputStream(new byte[0]));}}
  public void onPageFinished(WebView v,String url){if(url.startsWith("https://"+HOST+"/"))loaded.run();}
 });}
 static WebResourceResponse response(int code,String type,InputStream bytes){Map<String,String> h=new HashMap<>();h.put("Cache-Control","no-store");return new WebResourceResponse(type,type.startsWith("text/")||type.contains("json")?"UTF-8":null,code,code==200?"OK":code==204?"No Content":code==404?"Not Found":"Forbidden",h,bytes);}
 static String mime(String p){return p.endsWith(".html")?"text/html":p.endsWith(".mjs")||p.endsWith(".js")?"text/javascript":p.endsWith(".json")?"application/json":p.endsWith(".css")?"text/css":p.endsWith(".png")?"image/png":p.endsWith(".ttf")?"font/ttf":"text/plain";}
 void call(String js){evaluateJavascript("window.Dudu&&window.Dudu."+js,null);}
}
