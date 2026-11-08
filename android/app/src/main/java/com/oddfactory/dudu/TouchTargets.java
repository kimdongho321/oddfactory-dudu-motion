package com.oddfactory.dudu;
import android.content.Context;
import android.graphics.*;
import android.os.Build;
import android.view.*;
/**
 * 두두 그림 위에만 놓는 작은 터치 창 1개. 누름/이동/뗌을 화면 좌표 그대로 런타임에 넘기고
 * 톡/더블톡/꾹 누르기 판정은 공용 런타임(dudu-runtime.mjs)이 한다. 누르는 동안에는 창을 옮기지 않는다.
 */
final class TouchTargets {
 interface Listener {void pointer(String type,float x,float y);}
 final Context context;final WindowManager wm;final Listener listener;View view;WindowManager.LayoutParams layout;Rect wanted=new Rect();boolean visible,active,suppress;
 TouchTargets(Context c,WindowManager w,Listener l){context=c;wm=w;listener=l;}
 boolean touch(MotionEvent e){int a=e.getActionMasked();if(!visible)return true;
  if(e.getPointerCount()!=1||a==MotionEvent.ACTION_POINTER_DOWN){if(active)listener.pointer("cancel",e.getRawX(),e.getRawY());active=false;suppress=true;}
  if(suppress){if(a==MotionEvent.ACTION_UP||a==MotionEvent.ACTION_CANCEL){suppress=false;active=false;apply();}return true;}
  if(a==MotionEvent.ACTION_DOWN){active=true;listener.pointer("down",e.getRawX(),e.getRawY());}
  else if(a==MotionEvent.ACTION_MOVE&&active)listener.pointer("move",e.getRawX(),e.getRawY());
  else if(a==MotionEvent.ACTION_UP&&active){listener.pointer("up",e.getRawX(),e.getRawY());active=false;apply();}
  else if(a==MotionEvent.ACTION_CANCEL&&active){listener.pointer("cancel",e.getRawX(),e.getRawY());active=false;apply();}
  return true;}
 void update(Rect r){wanted=new Rect(r);if(!active)apply();}
 void visible(boolean value){if(visible==value)return;visible=value;if(!value&&active){listener.pointer("cancel",0,0);active=false;}apply();}
 void apply(){boolean use=visible&&!wanted.isEmpty();
  if(view==null){view=new View(context);view.setBackgroundColor(Color.TRANSPARENT);view.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);view.setOnTouchListener((v,e)->touch(e));}
  if(!use){if(layout!=null){try{wm.removeView(view);}catch(RuntimeException ignored){}layout=null;}return;}
  WindowManager.LayoutParams p=new WindowManager.LayoutParams(wanted.width(),wanted.height(),WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL|WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN|WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,PixelFormat.TRANSLUCENT);
  p.gravity=Gravity.TOP|Gravity.LEFT;p.setTitle("com.oddfactory.dudu.input");p.x=wanted.left;p.y=wanted.top;p.windowAnimations=0;
  if(Build.VERSION.SDK_INT>=30){p.setFitInsetsTypes(0);p.layoutInDisplayCutoutMode=WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS;}else if(Build.VERSION.SDK_INT>=28)p.layoutInDisplayCutoutMode=WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
  if(Build.VERSION.SDK_INT>=34)p.setCanPlayMoveAnimation(false);
  try{if(layout==null)wm.addView(view,p);else if(layout.x!=p.x||layout.y!=p.y||layout.width!=p.width||layout.height!=p.height)wm.updateViewLayout(view,p);layout=p;}catch(RuntimeException e){layout=null;}}
 void close(){visible(false);wanted=new Rect();apply();}
}
