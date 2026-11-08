package com.oddfactory.dudu;
import android.content.*;
import android.content.res.Configuration;
/** 저장 설정: 실행 여부, 크기, 야광 모드(auto|normal|glow). */
final class Prefs {
 static final float MIN_SCALE=0.3f,MAX_SCALE=1.2f,DEFAULT_SCALE=0.39f;
 static SharedPreferences of(Context c){return c.getSharedPreferences("pet",0);}
 static boolean enabled(Context c){return of(c).getBoolean("enabled",false);}
 static void enabled(Context c,boolean v){of(c).edit().putBoolean("enabled",v).apply();}
 static float scale(Context c){float s=of(c).getFloat("scale",DEFAULT_SCALE);return Float.isFinite(s)?Math.max(MIN_SCALE,Math.min(MAX_SCALE,s)):DEFAULT_SCALE;}
 static void scale(Context c,float v){of(c).edit().putFloat("scale",Math.max(MIN_SCALE,Math.min(MAX_SCALE,v))).apply();}
 static String glow(Context c){String v=of(c).getString("glow","auto");return "normal".equals(v)||"glow".equals(v)?v:"auto";}
 static void glow(Context c,String v){of(c).edit().putString("glow",v).apply();}
 static boolean systemDark(Context c){return (c.getResources().getConfiguration().uiMode&Configuration.UI_MODE_NIGHT_MASK)==Configuration.UI_MODE_NIGHT_YES;}
 /** 실제로 쓸 그림 세트: 자동이면 시스템 다크 모드를 따른다. */
 static String mode(Context c){String g=glow(c);if("auto".equals(g))return systemDark(c)?"glow":"normal";return g;}
}
