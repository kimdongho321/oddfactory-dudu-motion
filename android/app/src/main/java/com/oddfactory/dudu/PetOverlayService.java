package com.oddfactory.dudu;
import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.*;
import android.content.*;
import android.content.res.Configuration;
import android.graphics.*;
import android.os.*;
import android.view.*;
import android.view.accessibility.AccessibilityEvent;
import android.webkit.JavascriptInterface;
import android.widget.*;
/**
 * 화면 전체 크기의 투명·터치 불가 창(두두 그림) + 두두 그림 위에만 놓는 작은 터치 창.
 * 접근성 서비스는 오버레이 창을 띄우는 데만 쓰고 이벤트는 받지 않는다(eventTypes=0, 창 내용 읽기 없음).
 */
public final class PetOverlayService extends AccessibilityService {
 public static volatile PetOverlayService current;
 final Handler main=new Handler(Looper.getMainLooper());
 WindowManager manager;RuntimeView web;FrameLayout root;WindowManager.LayoutParams params;TouchTargets targets;Rect world;AlertDialog menu;
 boolean running,ready,awake,registered;int session;String mode;
 final BroadcastReceiver screen=new BroadcastReceiver(){public void onReceive(Context c,Intent i){visibility();}};
 protected void onServiceConnected(){current=this;manager=getSystemService(WindowManager.class);AccessibilityServiceInfo info=getServiceInfo();info.eventTypes=0;setServiceInfo(info);if(Prefs.enabled(this))startSession();MainActivity.overlayConnected(this);}
 public void startSession(){if(running){visibility();return;}running=true;ready=false;awake=false;Prefs.enabled(this,true);world=DisplayGeometry.world(manager);session++;foreground();
  final int id=session;mode=Prefs.mode(this);
  root=new FrameLayout(this);root.setBackgroundColor(Color.TRANSPARENT);
  web=new RuntimeView(this,new Host(id),()->{});root.addView(web,new FrameLayout.LayoutParams(world.width(),world.height()));
  params=new WindowManager.LayoutParams(world.width(),world.height(),WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE|WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL|WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN|WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,PixelFormat.TRANSLUCENT);
  params.gravity=Gravity.TOP|Gravity.LEFT;params.setTitle("com.oddfactory.dudu.overlay");params.x=world.left;params.y=world.top;params.windowAnimations=0;
  if(Build.VERSION.SDK_INT>=30){params.setFitInsetsTypes(0);params.layoutInDisplayCutoutMode=WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;}else if(Build.VERSION.SDK_INT>=28)params.layoutInDisplayCutoutMode=WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
  if(Build.VERSION.SDK_INT>=34)params.setCanPlayMoveAnimation(false);
  root.setVisibility(View.INVISIBLE);manager.addView(root,params);
  targets=new TouchTargets(this,manager,(type,x,y)->{if(web!=null&&world!=null)web.call("pointer('"+type+"',"+(x-world.left)+","+(y-world.top)+","+world.width()+","+world.height()+")");});
  IntentFilter f=new IntentFilter();f.addAction(Intent.ACTION_SCREEN_ON);f.addAction(Intent.ACTION_SCREEN_OFF);f.addAction(Intent.ACTION_USER_PRESENT);if(Build.VERSION.SDK_INT>=33)registerReceiver(screen,f,Context.RECEIVER_NOT_EXPORTED);else registerReceiver(screen,f);registered=true;
  web.loadUrl("https://"+RuntimeView.HOST+"/screen.html?scale="+Prefs.scale(this)+"&mode="+mode+"&hatched="+(Prefs.hatched(this)?1:0));
  visibility();}
 void foreground(){NotificationManager n=getSystemService(NotificationManager.class);n.createNotificationChannel(new NotificationChannel("pet",getString(R.string.app_name),NotificationManager.IMPORTANCE_LOW));PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);Notification notice=new Notification.Builder(this,"pet").setSmallIcon(android.R.drawable.star_on).setContentTitle(getString(R.string.pet_running)).setContentText("두두를 더블터치하면 설정·종료").setContentIntent(open).setOngoing(true).build();if(Build.VERSION.SDK_INT>=34)startForeground(27,notice,android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);else startForeground(27,notice);}
 /** 화면이 켜지고 잠금이 풀렸을 때만 보인다. 앱 설정 화면이 앞에 있으면 그림은 보이되 터치 창은 치운다(설정 버튼을 가리지 않게). */
 public void visibility(){if(!running||web==null)return;boolean next=getSystemService(PowerManager.class).isInteractive()&&!getSystemService(KeyguardManager.class).isKeyguardLocked();
  if(next!=awake){awake=next;if(awake){root.setVisibility(View.VISIBLE);web.onResume();}else{closeMenu();root.setVisibility(View.INVISIBLE);web.onPause();}}
  if(targets!=null)targets.visible(awake&&ready&&menu==null&&!MainActivity.visible);}
 final class Host {
  final int id;Host(int value){id=value;}
  boolean live(){return running&&session==id&&web!=null;}
  @JavascriptInterface public void ready(){main.post(()->{if(!live())return;ready=true;applySettings();visibility();});}
  @JavascriptInterface public void menu(){main.post(()->{if(live())showMenu();});}
  @JavascriptInterface public void hatched(){main.post(()->{if(live())Prefs.hatched(PetOverlayService.this,true);});}
  @JavascriptInterface public void bounds(String encoded){if(encoded==null||encoded.length()>200)return;main.post(()->{if(!live()||targets==null)return;try{String[] v=encoded.split(",");if(v.length!=6)return;double l=Double.parseDouble(v[0]),t=Double.parseDouble(v[1]),r=Double.parseDouble(v[2]),b=Double.parseDouble(v[3]),vw=Double.parseDouble(v[4]),vh=Double.parseDouble(v[5]);Rect hit=DisplayGeometry.bounds(l,t,r,b,vw,vh,world);int pad=AppUi.dp(PetOverlayService.this,4);hit.inset(-pad,-pad);hit.intersect(world);targets.update(hit);}catch(RuntimeException ignored){}});}
 }
 /** 크기·야광 설정을 지금 화면의 두두에 반영. */
 public void applySettings(){if(!running||web==null)return;mode=Prefs.mode(this);web.call("setScale("+Prefs.scale(this)+")");web.call("setMode('"+mode+"')");}
 public void restartEgg(){Prefs.hatched(this,false);if(running&&web!=null)web.call("restart()");}
 void closeMenu(){if(menu!=null){AlertDialog d=menu;menu=null;d.dismiss();}}
 void showMenu(){if(!running||!awake)return;closeMenu();if(targets!=null)targets.visible(false);
  LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(AppUi.dp(this,16),AppUi.dp(this,12),AppUi.dp(this,16),AppUi.dp(this,16));box.setBackgroundColor(AppUi.BG);box.addView(AppUi.text(this,getString(R.string.app_name),22,true));
  add(box,"설정",()->startActivity(new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)));
  add(box,"종료",this::stopSession);
  AlertDialog d=new AlertDialog.Builder(this).setView(box).create();d.getWindow().setType(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY);d.setOnDismissListener(v->{if(menu==d)menu=null;visibility();});menu=d;d.show();d.getWindow().setLayout(Math.min(world.width()-AppUi.dp(this,32),AppUi.dp(this,300)),-2);AppUi.fonts(this,d.getWindow().getDecorView());}
 void add(LinearLayout box,String text,Runnable task){Button button=AppUi.button(this,text,false,()->{closeMenu();task.run();});LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=AppUi.dp(this,10);box.addView(button,p);}
 public void stopSession(){Prefs.enabled(this,false);closeSession();}
 void closeSession(){session++;running=false;ready=false;awake=false;closeMenu();main.removeCallbacksAndMessages(null);if(registered){try{unregisterReceiver(screen);}catch(RuntimeException ignored){}registered=false;}if(targets!=null){targets.close();targets=null;}if(root!=null){try{manager.removeView(root);}catch(RuntimeException ignored){}root=null;}if(web!=null){web.stopLoading();web.destroy();web=null;}stopForeground(STOP_FOREGROUND_REMOVE);}
 public void onConfigurationChanged(Configuration c){super.onConfigurationChanged(c);if(!running||web==null)return;
  Rect next=DisplayGeometry.world(manager);if(!next.equals(world)){world=next;closeMenu();if(targets!=null)targets.update(new Rect());params.x=world.left;params.y=world.top;params.width=world.width();params.height=world.height();web.setLayoutParams(new FrameLayout.LayoutParams(world.width(),world.height()));try{manager.updateViewLayout(root,params);}catch(RuntimeException ignored){}web.call("fit()");}
  if(ready&&!Prefs.mode(this).equals(mode))applySettings();}
 public void onAccessibilityEvent(AccessibilityEvent e){}
 public void onInterrupt(){}
 public boolean onUnbind(Intent intent){closeSession();current=null;return super.onUnbind(intent);}
 public void onDestroy(){closeSession();current=null;super.onDestroy();}
}
