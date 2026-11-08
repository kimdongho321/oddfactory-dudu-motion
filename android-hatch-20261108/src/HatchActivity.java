package com.oddfactory.duduhatch;

import android.app.Activity;
import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.*;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.*;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.*;
import java.io.IOException;

public final class HatchActivity extends Activity {
    static final int INK=0xff323527, PAPER=0xfff8f3e8, CREAM=0xfffffbf2, OLIVE=0xff566a42;
    private EggView stage;
    private TextView hint, count;
    private Button replay;
    private Typeface regular=Typeface.DEFAULT, bold=Typeface.DEFAULT_BOLD;

    int dp(float n){return Math.round(getResources().getDisplayMetrics().density*n);}
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        getWindow().setStatusBarColor(PAPER);
        getWindow().setNavigationBarColor(PAPER);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        try {
            regular=Typeface.createFromAsset(getAssets(),"maple-light.ttf");
            bold=Typeface.createFromAsset(getAssets(),"maple-bold.ttf");
        } catch(RuntimeException ignored) {}
        LinearLayout root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setPadding(dp(18),dp(8),dp(18),dp(12)); root.setBackgroundColor(PAPER);
        root.addView(label("두두의 알",28,true,INK),new LinearLayout.LayoutParams(-1,dp(51)));
        stage=new EggView(this);
        root.addView(stage,new LinearLayout.LayoutParams(-1,0,1));
        hint=label("",19,true,INK);
        root.addView(hint,new LinearLayout.LayoutParams(-1,dp(39)));
        count=label("",14,false,OLIVE);
        count.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        root.addView(count,new LinearLayout.LayoutParams(-1,dp(23)));
        replay=new Button(this); replay.setText("다시 부화하기"); replay.setAllCaps(false); replay.setTypeface(bold);
        replay.setBackgroundTintList(ColorStateList.valueOf(0xffdce8c7));
        replay.setTextColor(INK); replay.setOnClickListener(v->stage.reset());
        root.addView(replay,new LinearLayout.LayoutParams(dp(160),dp(47)));
        setContentView(root);
        if(state!=null) stage.restore(state.getInt("taps"),state.getLong("hatchMs"),state.getBoolean("hatched"));
        updateLabels();
    }
    private TextView label(String text,int sp,boolean strong,int color){
        TextView v=new TextView(this); v.setText(text); v.setTextSize(sp);
        v.setTextColor(color); v.setTypeface(strong?bold:regular); v.setGravity(Gravity.CENTER); return v;
    }
    void updateLabels(){
        if(hint==null)return;
        int taps=stage.taps; boolean done=stage.done;
        hint.setText(done?"두두가 나왔어요!":taps==3?"알이 열리고 있어요!":taps==2?"한 번 더 톡!":taps==1?"알이 움직여요!":"알을 톡톡 두드려 봐요");
        count.setText(taps+" / 3");
        stage.setContentDescription(done?"부화한 두두":taps==3?"부화 중":"공룡알 두드리기, "+taps+" / 3");
        stage.setClickable(taps<3);
        replay.setVisibility(done?View.VISIBLE:View.INVISIBLE);
    }
    @Override protected void onSaveInstanceState(Bundle state){
        super.onSaveInstanceState(state);
        state.putInt("taps",stage.taps);
        state.putBoolean("hatched",stage.done);
        state.putLong("hatchMs",stage.elapsed());
    }

    private final class EggView extends View {
        final int SW=306, SH=281;
        final Bitmap[] egg=new Bitmap[4], emerge=new Bitmap[5];
        final Bitmap standing;
        final Paint sprite=new Paint(), paint=new Paint();
        final RectF bounds=new RectF(), dst=new RectF();
        final Matrix hitMap=new Matrix(), invMap=new Matrix();
        final float[] touch=new float[2];
        final int touchSlop;
        int taps=0, pointer=-1;
        long shakeAt=-10_000, hatchAt, spawned=SystemClock.uptimeMillis();
        boolean done;
        float downX, downY;
        float centerX, ground, scale;

        EggView(Context ctx) {
            super(ctx);
            setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_YES);
            setFocusable(true);
            touchSlop=ViewConfiguration.get(ctx).getScaledTouchSlop();
            sprite.setFilterBitmap(false); sprite.setAntiAlias(false); sprite.setDither(false);
            for(int i=0;i<4;i++)egg[i]=load("egg-"+i+".png");
            for(int i=0;i<5;i++)emerge[i]=load("hatch-"+(i+1)+".png");
            standing=load("standing.png");
        }
        Bitmap load(String name){
            BitmapFactory.Options options=new BitmapFactory.Options(); options.inScaled=false;
            try(java.io.InputStream in=getAssets().open(name)){
                Bitmap b=BitmapFactory.decodeStream(in,null,options);
                if(b==null || b.getWidth()!=SW || b.getHeight()!=SH)throw new IllegalStateException(name);
                return b;
            }catch(IOException e){throw new IllegalStateException(name,e);}
        }
        long elapsed(){return taps==3?Math.max(0,SystemClock.uptimeMillis()-hatchAt):0;}
        void restore(int previous,long ms,boolean finished){
            taps=Math.max(0,Math.min(3,previous)); done=taps==3&&finished;
            if(taps==3) hatchAt=SystemClock.uptimeMillis()-Math.min(1100,ms);
            spawned=-10_000;
        }
        void reset(){
            taps=0; pointer=-1; done=false; shakeAt=-10_000; hatchAt=0; spawned=SystemClock.uptimeMillis();
            updateLabels(); invalidate();
        }
        @Override public boolean performClick(){
            if(taps>=3)return false;
            super.performClick();
            taps++; shakeAt=SystemClock.uptimeMillis();
            if(taps==3) hatchAt=shakeAt;
            performHapticFeedback(taps==3?HapticFeedbackConstants.LONG_PRESS:HapticFeedbackConstants.VIRTUAL_KEY);
            updateLabels(); invalidate(); return true;
        }
        @Override public void onInitializeAccessibilityNodeInfo(AccessibilityNodeInfo info){
            super.onInitializeAccessibilityNodeInfo(info);
            if(taps<3)info.setClassName("android.widget.Button");
        }
        boolean overEgg(float x,float y){
            if(taps>=3 || !hitMap.invert(invMap))return false;
            touch[0]=x;touch[1]=y;invMap.mapPoints(touch);
            int ix=(int)Math.floor(touch[0]), iy=(int)Math.floor(touch[1]);
            return ix>=0&&ix<SW&&iy>=0&&iy<SH&&Color.alpha(egg[0].getPixel(ix,iy))>128;
        }
        @Override public boolean onTouchEvent(MotionEvent e){
            switch(e.getActionMasked()){
                case MotionEvent.ACTION_DOWN:
                    if(!overEgg(e.getX(),e.getY()))return false;
                    pointer=e.getPointerId(0); downX=e.getX();downY=e.getY();return true;
                case MotionEvent.ACTION_POINTER_DOWN: pointer=-1; return true;
                case MotionEvent.ACTION_CANCEL: pointer=-1;return true;
                case MotionEvent.ACTION_UP:
                    boolean activate=pointer==e.getPointerId(0)&&Math.hypot(e.getX()-downX,e.getY()-downY)<=touchSlop;
                    pointer=-1; if(activate)performClick(); return true;
                default:return true;
            }
        }
        void shape(Canvas c,int color,float l,float t,float r,float b){
            paint.setColor(color); c.drawRect(l,t,r,b,paint);
        }
        @Override protected void onDraw(Canvas c){
            super.onDraw(c);
            float w=getWidth(), h=getHeight();
            if(w==0||h==0)return;
            paint.setAntiAlias(true);
            paint.setColor(CREAM); bounds.set(0,0,w,h);c.drawRoundRect(bounds,dp(24),dp(24),paint);
            float ideal=Math.min(w*.94f/SW,h*.94f/SH);
            scale=ideal>=1?(float)Math.floor(ideal):ideal;
            centerX=Math.round(w/2); ground=Math.round(h*.8f);
            long now=SystemClock.uptimeMillis(), ms=elapsed(), shake=now-shakeAt, spawn=now-spawned;
            Bitmap b=egg[Math.min(taps,3)]; float y=0, angle=0; boolean anim=false;
            if(taps<3){
                if(shake>=0&&shake<390){
                    angle=(float)(Math.sin(shake/390.0*Math.PI*6)*Math.pow(1-shake/390.0,1.55)*(taps==1?9:15));
                    y=(float)(-Math.abs(Math.sin(shake/390.0*Math.PI*3))*3*(1-shake/390.0)); anim=true;
                }
                if(spawn>=0&&spawn<270&&taps==0){
                    double t=spawn/270.0;
                    y=(float)(-19*(1-t)*(1-t)); anim=true;
                }
            } else if(!done) {
                if(ms<105){angle=(float)(Math.sin(ms/105.0*Math.PI*3)*8);y=-2;}
                else if(ms<230)b=emerge[0];
                else if(ms<460)b=emerge[1];
                else if(ms<600)b=emerge[2];
                else if(ms<845){
                    b=emerge[3];double t=(ms-600)/245.0;y=(float)(-20*Math.sin(Math.PI*t));
                }else if(ms<1010)b=emerge[4];
                else {done=true;b=standing;post(HatchActivity.this::updateLabels);}
                anim=!done;
            } else b=standing;
            int save=c.save();
            c.translate(centerX,ground);c.scale(scale,scale);
            paint.setColor(0xffe6dac5); bounds.set(taps==3?-67:-50,-4,taps==3?67:50,7); c.drawOval(bounds,paint);
            c.rotate(angle,0,-5);
            dst.set(-153,-260+Math.round(y),153,21+Math.round(y));
            c.drawBitmap(b,null,dst,sprite); c.restoreToCount(save);
            hitMap.reset(); hitMap.setTranslate(-153,-260+Math.round(y)); hitMap.postRotate(angle,0,-5);
            hitMap.postScale(scale,scale);hitMap.postTranslate(centerX,ground);
            if(taps==3&&ms>=590&&ms<1060) {
                int s=c.save();c.translate(centerX,ground);c.scale(scale,scale); burst(c,(ms-590)/470f);c.restoreToCount(s);
                if(ms<1060)anim=true;
            }
            if(anim)postInvalidateOnAnimation();
        }
        void burst(Canvas c,float t){
            paint.setAntiAlias(false);
            for(int i=0;i<10;i++){
                double a=(i+0.22)*Math.PI/5;
                float x=Math.round(Math.cos(a)*(27+84*t)), y=Math.round(-82+Math.sin(a)*(19+56*t)+77*t*t);
                float s=i%3==0?6:4;
                Path path=new Path();path.moveTo(x-s,y+s);path.lineTo(x,y-s);path.lineTo(x+s,y-1);path.lineTo(x+s-2,y+s-2);path.close();
                paint.setColor(i%2==0?0xff966034:0xff6f5832);c.drawPath(path,paint);
                shape(c,0xfff4c36d,x-1,y-1,x+2,y+1);
            }
            if(t<.43){
                float x=82+20*t,y=-143-13*t;
                shape(c,0xffffd480,x-2,y-12,x+2,y+12);shape(c,0xffffd480,x-12,y-2,x+12,y+2);
                shape(c,0xfffffae1,x-3,y-3,x+3,y+3);
            }
        }
    }
}
