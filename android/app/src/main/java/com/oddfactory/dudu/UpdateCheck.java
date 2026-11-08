package com.oddfactory.dudu;
import android.app.*;
import android.content.*;
import android.net.Uri;
import android.os.SystemClock;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.*;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import javax.net.ssl.HttpsURLConnection;
/**
 * GitHub 최신 릴리스(kimdongho321/oddfactory-dudu-motion)의 tag_name과 앱 versionName을 비교한다.
 * 새 버전이면 릴리스 페이지를 브라우저로 연다. 다른 정보는 보내거나 저장하지 않는다.
 */
final class UpdateCheck {
 static final String REPO="kimdongho321/oddfactory-dudu-motion";
 static final String API="https://api.github.com/repos/"+REPO+"/releases/latest";
 static final String PAGE="https://github.com/"+REPO+"/releases";
 static final int MAX_BYTES=256*1024,TIMEOUT_MS=8000;
 final Activity activity;boolean running,shown;AlertDialog dialog;
 UpdateCheck(Activity a){activity=a;}
 /** requested=false: 앱을 열 때 한 번 조용히(새 버전 있을 때만 알림). */
 void check(boolean requested){if(running)return;if(!requested&&shown)return;shown=true;running=true;if(requested)toast("새 버전을 확인하고 있어요.");
  String installed=installedVersion();
  new Thread(()->{String tag=null,url=null;int status=0;boolean failed=false;
   try{HttpsURLConnection c=(HttpsURLConnection)new URL(API).openConnection();try{c.setInstanceFollowRedirects(true);c.setConnectTimeout(TIMEOUT_MS);c.setReadTimeout(TIMEOUT_MS);c.setUseCaches(false);c.setRequestProperty("Accept","application/vnd.github+json");c.setRequestProperty("User-Agent","oddfactory-dudu/"+installed);status=c.getResponseCode();
    if(status==200){try(InputStream in=c.getInputStream()){ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[4096];int n;while((n=in.read(b))!=-1){if(out.size()+n>MAX_BYTES)throw new IOException("too large");out.write(b,0,n);}JSONObject j=new JSONObject(new String(out.toByteArray(),StandardCharsets.UTF_8));tag=j.optString("tag_name","");url=j.optString("html_url","");}}
   }finally{c.disconnect();}}catch(Exception e){failed=true;}
   String t=tag,u=url;int s=status;boolean f=failed;activity.runOnUiThread(()->deliver(requested,installed,t,u,s,f));},"update-check").start();}
 void deliver(boolean requested,String installed,String tag,String url,int status,boolean failed){running=false;if(activity.isFinishing()||activity.isDestroyed())return;
  if(status==404){if(requested)toast("아직 공개된 새 버전이 없어요.");return;}
  if(failed||status!=200||tag==null||tag.isEmpty()){if(requested)toast("업데이트를 확인할 수 없어요. 인터넷 연결을 확인하고 잠시 후 다시 시도해 주세요.");return;}
  String latest=tag.startsWith("v")||tag.startsWith("V")?tag.substring(1):tag;
  if(compare(latest,installed)<=0){if(requested)toast("최신 버전("+installed+")을 사용 중이에요.");return;}
  String open=url!=null&&url.startsWith("https://github.com/"+REPO+"/")?url:PAGE;
  if(dialog!=null)dialog.dismiss();
  dialog=new AlertDialog.Builder(activity).setTitle("새 버전이 있어요").setMessage("지금 버전: "+installed+"\n새 버전: "+latest+"\n\nGitHub 릴리스 페이지에서 APK를 받아 설치해 주세요.").setPositiveButton("릴리스 페이지 열기",(d,w)->{try{activity.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(open)));}catch(ActivityNotFoundException e){toast("링크를 열 앱이 없어요.");}}).setNegativeButton("나중에",null).create();
  dialog.setOnShowListener(d->AppUi.fonts(activity,dialog.getWindow().getDecorView()));dialog.setOnDismissListener(d->dialog=null);dialog.show();}
 String installedVersion(){try{return activity.getPackageManager().getPackageInfo(activity.getPackageName(),0).versionName;}catch(Exception e){return "0";}}
 /** 1.2.10 > 1.2.9 처럼 숫자 단위로 비교. 숫자 아닌 꼬리(-beta 등)는 무시. */
 static int compare(String a,String b){String[] x=a.split("[.]"),y=b.split("[.]");for(int i=0;i<Math.max(x.length,y.length);i++){int p=i<x.length?num(x[i]):0,q=i<y.length?num(y[i]):0;if(p!=q)return Integer.compare(p,q);}return 0;}
 static int num(String s){int n=0,i=0;while(i<s.length()&&Character.isDigit(s.charAt(i))&&i<9){n=n*10+(s.charAt(i)-'0');i++;}return n;}
 void toast(String s){Toast.makeText(activity,s,Toast.LENGTH_SHORT).show();}
 void close(){if(dialog!=null)dialog.dismiss();}
}
