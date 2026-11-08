package com.oddfactory.dudu;
import android.app.*;
import android.content.*;
import android.content.res.Configuration;
import android.graphics.*;
import android.os.*;
import android.view.*;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.widget.*;
/**
 * 두두 그림 영역에만 불투명도 100%의 창을 놓는다.
 */
public final class PetOverlayService extends Service {
 public static volatile PetOverlayService current;
 final Handler main=new Handler(Looper.getMainLooper());
 WindowManager manager;RuntimeView web;PetWindow pet;Rect world;AlertDialog menu;
 boolean running,ready,awake,registered;int session;String mode;
 final BroadcastReceiver screen=new BroadcastReceiver(){public void onReceive(Context c,Intent i){visibility();}};
 @Override public void onCreate(){super.onCreate();current=this;manager=getSystemService(WindowManager.class);}
 @Override public IBinder onBind(Intent intent){return null;}
 @Override public int onStartCommand(Intent intent,int flags,int startId){
  if(!Settings.canDrawOverlays(this)||!Prefs.enabled(this)){stopSelf();return START_NOT_STICKY;}
  try{startSession();}
  catch(RuntimeException failure){
   Prefs.enabled(this,false);
   closeSession();
   stopSelf();
   MainActivity.overlayStartFailed();
   return START_NOT_STICKY;
  }
  MainActivity.overlayConnected(this);
  return START_STICKY;
 }
 public void startSession(){if(running){visibility();return;}running=true;ready=false;awake=false;Prefs.enabled(this,true);world=DisplayGeometry.world(manager);session++;foreground();
  final int id=session;mode=Prefs.mode(this);
  web = new RuntimeView(this, new Host(id), () -> {});
  pet = new PetWindow(this, manager, web, world, (type, x, y) -> {
   if (web != null && world != null) {
    web.call("pointer('" + type + "'," + (x - world.left) + "," + (y - world.top)
      + "," + world.width() + "," + world.height() + ")");
   }
  });
  pet.attach();
  IntentFilter f=new IntentFilter();f.addAction(Intent.ACTION_SCREEN_ON);f.addAction(Intent.ACTION_SCREEN_OFF);f.addAction(Intent.ACTION_USER_PRESENT);if(Build.VERSION.SDK_INT>=33)registerReceiver(screen,f,Context.RECEIVER_NOT_EXPORTED);else registerReceiver(screen,f);registered=true;
  web.loadUrl("https://"+RuntimeView.HOST+"/screen.html?scale="+Prefs.scale(this)+"&mode="+mode+"&hatched="+(Prefs.hatched(this)?1:0));
  visibility();}
 void foreground(){NotificationManager n=getSystemService(NotificationManager.class);n.createNotificationChannel(new NotificationChannel("pet",getString(R.string.app_name),NotificationManager.IMPORTANCE_LOW));PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);Notification notice=new Notification.Builder(this,"pet").setSmallIcon(android.R.drawable.star_on).setContentTitle(getString(R.string.pet_running)).setContentText("두두를 더블터치하면 설정·알부터 다시·종료").setContentIntent(open).setOngoing(true).build();if(Build.VERSION.SDK_INT>=34)startForeground(27,notice,android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);else startForeground(27,notice);}
 /** 화면이 켜지고 잠금이 풀렸을 때만 보인다. 설정 버튼을 가리지 않도록 앱 설정 중에는 창을 숨긴다. */
 public void visibility(){if(!running||web==null)return;boolean next=getSystemService(PowerManager.class).isInteractive()&&!getSystemService(KeyguardManager.class).isKeyguardLocked();
  if(next!=awake){awake=next;if(awake){web.onResume();}else{closeMenu();web.onPause();}}
  if(pet!=null)pet.show(awake&&ready&&menu==null&&!MainActivity.visible);}
 final class Host {
  final int id;Host(int value){id=value;}
  boolean live(){return running&&session==id&&web!=null;}
  @JavascriptInterface public void ready(){main.post(()->{if(!live())return;ready=true;applySettings();visibility();});}
  @JavascriptInterface public void menu(){main.post(()->{if(live())showMenu();});}
  @JavascriptInterface public void hatched(){main.post(()->{if(live())Prefs.hatched(PetOverlayService.this,true);});}
  @JavascriptInterface public void bounds(String encoded) {
   if (encoded == null || encoded.length() > 200) return;
   main.post(() -> {
    if (!live() || pet == null) return;
    String[] values = encoded.split(",");
    if (values.length != 6) return;
    try {
     Rect area = DisplayGeometry.bounds(
       Double.parseDouble(values[0]), Double.parseDouble(values[1]),
       Double.parseDouble(values[2]), Double.parseDouble(values[3]),
       Double.parseDouble(values[4]), Double.parseDouble(values[5]), world);
     if (!area.isEmpty()) {
      int padding = AppUi.dp(PetOverlayService.this, 4);
      area.inset(-padding, -padding);
      if (!area.intersect(world)) area.setEmpty();
     }
     pet.place(area);
    } catch (IllegalArgumentException ignored) {
     // Ignore malformed bounds reported by the renderer.
    }
   });
  }
 }
 /** 크기·야광 설정을 지금 화면의 두두에 반영. */
 public void applySettings(){if(!running||web==null)return;mode=Prefs.mode(this);web.call("setScale("+Prefs.scale(this)+")");web.call("setMode('"+mode+"')");}
 public void restartEgg(){Prefs.hatched(this,false);if(running&&web!=null)web.call("restart()");}
 void closeMenu(){if(menu!=null){AlertDialog d=menu;menu=null;d.dismiss();}}
 void showMenu(){if(!running||!awake)return;closeMenu();if(pet!=null)pet.show(false);
  LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(AppUi.dp(this,16),AppUi.dp(this,12),AppUi.dp(this,16),AppUi.dp(this,16));box.setBackgroundColor(AppUi.BG);box.addView(AppUi.text(this,getString(R.string.app_name),22,true));
  add(box,"설정",()->startActivity(new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)));
  add(box,"알부터 다시",this::restartEgg);
  add(box,"종료",this::stopSession);
  AlertDialog d=new AlertDialog.Builder(this).setView(box).create();d.getWindow().setType(WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY);d.setOnDismissListener(v->{if(menu==d)menu=null;visibility();});menu=d;d.show();d.getWindow().setLayout(Math.min(world.width()-AppUi.dp(this,32),AppUi.dp(this,300)),-2);AppUi.fonts(this,d.getWindow().getDecorView());}
 void add(LinearLayout box,String text,Runnable task){Button button=AppUi.button(this,text,false,()->{closeMenu();task.run();});LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=AppUi.dp(this,10);box.addView(button,p);}
 public void stopSession(){Prefs.enabled(this,false);closeSession();stopSelf();}
 void closeSession(){session++;running=false;ready=false;awake=false;closeMenu();main.removeCallbacksAndMessages(null);if(registered){try{unregisterReceiver(screen);}catch(RuntimeException ignored){}registered=false;}if(pet!=null){pet.close();pet=null;}if(web!=null){web.stopLoading();web.destroy();web=null;}stopForeground(STOP_FOREGROUND_REMOVE);}
 public void onConfigurationChanged(Configuration c){super.onConfigurationChanged(c);if(!running||web==null)return;
  Rect next=DisplayGeometry.world(manager);if(!next.equals(world)){world=next;closeMenu();if(pet!=null)pet.resizeWorld(world);web.call("fit()");}
  if(ready&&!Prefs.mode(this).equals(mode))applySettings();}
 public void onDestroy(){closeSession();current=null;super.onDestroy();}
}
