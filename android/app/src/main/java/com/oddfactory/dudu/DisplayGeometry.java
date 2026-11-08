package com.oddfactory.dudu;
import android.os.Build;
import android.graphics.Rect;
import android.util.DisplayMetrics;
import android.view.*;
final class DisplayGeometry {
 static Rect world(WindowManager wm){if(Build.VERSION.SDK_INT>=30)return new Rect(wm.getMaximumWindowMetrics().getBounds());DisplayMetrics m=new DisplayMetrics();wm.getDefaultDisplay().getRealMetrics(m);return new Rect(0,0,m.widthPixels,m.heightPixels);}
 /** CSS 좌표(l,t,r,b; 뷰포트 vw x vh) -> 화면 픽셀 사각형. 화면 밖은 잘라낸다. */
 static Rect bounds(double l,double t,double r,double b,double vw,double vh,Rect w){if(!Double.isFinite(vw)||!Double.isFinite(vh)||vw<=0||vh<=0||!Double.isFinite(l)||!Double.isFinite(t)||!Double.isFinite(r)||!Double.isFinite(b))throw new IllegalArgumentException();int x=(int)Math.max(0,Math.min(w.width(),Math.floor(l*w.width()/vw))),y=(int)Math.max(0,Math.min(w.height(),Math.floor(t*w.height()/vh)));int right=(int)Math.max(x,Math.min(w.width(),Math.ceil(r*w.width()/vw))),bottom=(int)Math.max(y,Math.min(w.height(),Math.ceil(b*w.height()/vh)));return new Rect(w.left+x,w.top+y,w.left+right,w.top+bottom);}
}
