package com.oddfactory.dudu;
import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.*;
import android.widget.*;
/** 키디언 AppUi와 같은 구성(메이플스토리 Light/Bold, 둥근 버튼). 색은 두두 부화 앱 팔레트. */
final class AppUi {
 static final int INK=0xff323527,BG=0xfff8f3e8,ACCENT=0xff566a42,SOFT=0xffece6d6,MUTED=0xff6b6c5c;
 static int dp(Context c,float n){return Math.round(n*c.getResources().getDisplayMetrics().density);}
 private static Typeface mapleLight,mapleBold;
 static synchronized Typeface font(Context c,boolean bold){try{if(bold){if(mapleBold==null)mapleBold=Typeface.createFromAsset(c.getAssets(),"fonts/Maplestory-Bold.ttf");return mapleBold;}if(mapleLight==null)mapleLight=Typeface.createFromAsset(c.getAssets(),"fonts/Maplestory-Light.ttf");return mapleLight;}catch(RuntimeException e){return bold?Typeface.DEFAULT_BOLD:Typeface.DEFAULT;}}
 static TextView text(Context c,String s,int size,boolean bold){TextView v=new TextView(c);v.setText(s);v.setTextSize(size);v.setTextColor(INK);v.setTypeface(font(c,bold));v.setLineSpacing(0,1.15f);return v;}
 static TextView muted(Context c,String s,int size){TextView v=text(c,s,size,false);v.setTextColor(MUTED);return v;}
 static Button button(Context c,String s,boolean primary,Runnable action){Button v=new Button(c);v.setText(s);v.setAllCaps(false);v.setTextSize(primary?22:16);v.setTypeface(font(c,primary));v.setTextColor(primary?-1:INK);v.setMinHeight(dp(c,primary?64:48));GradientDrawable bg=new GradientDrawable();bg.setColor(primary?ACCENT:SOFT);bg.setCornerRadius(dp(c,16));v.setBackground(bg);v.setPadding(dp(c,16),dp(c,10),dp(c,16),dp(c,10));v.setOnClickListener(w->action.run());return v;}
 static RadioButton radio(Context c,String s){RadioButton r=new RadioButton(c);r.setText(s);r.setTextSize(16);r.setTextColor(INK);r.setTypeface(font(c,false));r.setButtonTintList(ColorStateList.valueOf(ACCENT));r.setMinHeight(dp(c,44));return r;}
 static void fonts(Context c,View v){if(v instanceof TextView)((TextView)v).setTypeface(font(c,v instanceof Button));if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++)fonts(c,g.getChildAt(i));}}
}
