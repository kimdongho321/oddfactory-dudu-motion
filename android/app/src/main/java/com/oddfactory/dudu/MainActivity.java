package com.oddfactory.dudu;
import android.app.*;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.*;
import android.content.res.Configuration;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.view.accessibility.AccessibilityManager;
import android.widget.*;
import java.lang.ref.WeakReference;
/** 실행·설정 화면. 두두 더블터치 메뉴의 "설정"도 여기로 온다. */
public final class MainActivity extends Activity {
 public static boolean visible;private static WeakReference<MainActivity> foreground=new WeakReference<>(null);
 private boolean resumed,pendingStart,waitingForPermission;private TextView state,sizeValue,glowState;private UpdateCheck updates;
 int dp(float n){return AppUi.dp(this,n);}
 boolean allowed(){if(PetOverlayService.current!=null)return true;AccessibilityManager a=getSystemService(AccessibilityManager.class);for(AccessibilityServiceInfo info:a.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)){android.content.pm.ServiceInfo s=info.getResolveInfo().serviceInfo;if(getPackageName().equals(s.packageName)&&PetOverlayService.class.getName().equals(s.name))return true;}return false;}
 boolean foregroundOwner(){return resumed&&foreground.get()==this&&!isFinishing()&&!isDestroyed();}
 static void overlayConnected(PetOverlayService connected){MainActivity owner=foreground.get();if(owner==null)return;owner.runOnUiThread(()->{if(foreground.get()==owner&&PetOverlayService.current==connected&&owner.foregroundOwner()){owner.startIfReady();owner.refresh();}});}
 public void onCreate(Bundle b){super.onCreate(b);getWindow().setStatusBarColor(AppUi.BG);getWindow().setNavigationBarColor(AppUi.BG);getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);updates=new UpdateCheck(this);
  ScrollView scroll=new ScrollView(this);scroll.setBackgroundColor(AppUi.BG);LinearLayout column=new LinearLayout(this);column.setOrientation(LinearLayout.VERTICAL);column.setPadding(dp(20),dp(18),dp(20),dp(28));column.setBackgroundColor(AppUi.BG);scroll.addView(column);
  scroll.setOnApplyWindowInsetsListener((v,insets)->{if(Build.VERSION.SDK_INT>=30){android.graphics.Insets i=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());v.setPadding(i.left,i.top,i.right,i.bottom);}else v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});setContentView(scroll);
  add(column,AppUi.text(this,getString(R.string.app_name),28,true),-2);
  add(column,AppUi.text(this,"화면 위를 돌아다니는 꼬마 공룡 두두. 알을 세 번 톡톡 두드려 깨워 주세요.",16,false),-2);
  add(column,AppUi.button(this,"실행",true,this::execute),64);
  state=AppUi.text(this,"",14,false);add(column,state,-2);
  add(column,AppUi.muted(this,"톡: 간지럼  ·  꾹 누른 채 끌기: 들어서 옮기기\n더블터치: 설정·종료 메뉴",14),-2);
  // 크기 조절
  add(column,AppUi.text(this,"크기",19,true),-2);
  LinearLayout sizeRow=new LinearLayout(this);sizeRow.setOrientation(LinearLayout.HORIZONTAL);sizeRow.setGravity(Gravity.CENTER_VERTICAL);
  SeekBar size=new SeekBar(this);int steps=Math.round((Prefs.MAX_SCALE-Prefs.MIN_SCALE)*100);size.setMax(steps);size.setProgress(Math.round((Prefs.scale(this)-Prefs.MIN_SCALE)*100));size.setProgressTintList(android.content.res.ColorStateList.valueOf(AppUi.ACCENT));size.setThumbTintList(android.content.res.ColorStateList.valueOf(AppUi.ACCENT));size.setContentDescription("두두 크기");
  sizeValue=AppUi.text(this,"",16,true);sizeValue.setMinWidth(dp(56));sizeValue.setGravity(Gravity.END);
  sizeRow.addView(size,new LinearLayout.LayoutParams(0,dp(48),1));sizeRow.addView(sizeValue,new LinearLayout.LayoutParams(-2,-2));add(column,sizeRow,-2);
  size.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int p,boolean user){if(!user)return;Prefs.scale(MainActivity.this,Prefs.MIN_SCALE+p/100f);showSize();if(PetOverlayService.current!=null)PetOverlayService.current.applySettings();}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});
  showSize();add(column,AppUi.muted(this,"두두가 화면에 나와 있으면 바로 바뀌어요.",13),-2);
  // 야광 모드
  add(column,AppUi.text(this,"야광 모드",19,true),-2);
  RadioGroup glow=new RadioGroup(this);glow.setOrientation(RadioGroup.VERTICAL);String[][] options={{"auto","자동 (휴대폰 다크 모드를 따라가요)"},{"normal","항상 일반"},{"glow","항상 야광"}};
  for(int i=0;i<options.length;i++){RadioButton r=AppUi.radio(this,options[i][1]);r.setId(View.generateViewId());r.setTag(options[i][0]);glow.addView(r);if(options[i][0].equals(Prefs.glow(this)))r.setChecked(true);}
  glow.setOnCheckedChangeListener((g,id)->{View v=g.findViewById(id);if(v==null)return;Prefs.glow(this,(String)v.getTag());showGlow();if(PetOverlayService.current!=null)PetOverlayService.current.applySettings();});
  add(column,glow,-2);glowState=AppUi.muted(this,"",13);add(column,glowState,-2);showGlow();
  // 기타
  add(column,AppUi.button(this,"알부터 다시 보기",false,()->{if(PetOverlayService.current!=null&&PetOverlayService.current.running){PetOverlayService.current.restartEgg();Toast.makeText(this,"두두가 다시 알로 돌아갔어요.",Toast.LENGTH_SHORT).show();}else{Prefs.hatched(this,false);Toast.makeText(this,"다음 실행 때 알부터 시작해요.",Toast.LENGTH_SHORT).show();}}),48);
  add(column,AppUi.button(this,"업데이트 확인 (현재 "+updates.installedVersion()+")",false,()->updates.check(true)),48);
  add(column,AppUi.button(this,"권한 안내",false,this::permissionGuide),48);
  add(column,AppUi.button(this,"글꼴·이용 고지",false,this::licenses),48);
  add(column,AppUi.button(this,"종료 (두두 숨기기)",false,()->{Prefs.enabled(this,false);if(PetOverlayService.current!=null)PetOverlayService.current.stopSession();refresh();}),48);
  add(column,AppUi.muted(this,"트릭컬 팬아트로 만든 비상업 팬메이드 앱이에요.",12),-2);
  updates.check(false);
 }
 void showSize(){sizeValue.setText(Math.round(Prefs.scale(this)*100)+"%");}
 void showGlow(){String g=Prefs.glow(this);glowState.setText("지금: "+("glow".equals(Prefs.mode(this))?"야광":"일반")+("auto".equals(g)?" (휴대폰 다크 모드 "+(Prefs.systemDark(this)?"켜짐":"꺼짐")+")":""));}
 void add(LinearLayout parent,View v,int height){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,height<0?height:dp(height));p.topMargin=dp(12);parent.addView(v,p);}
 void notice(String title,String text){AlertDialog d=new AlertDialog.Builder(this).setTitle(title).setMessage(text).setPositiveButton("확인",null).create();d.setOnShowListener(v->AppUi.fonts(this,d.getWindow().getDecorView()));d.show();}
 static final String PERMISSION_TEXT="두두가 다른 앱과 홈 화면 위를 돌아다니려면 접근성 설정에서 \"두두\"를 한 번 켜 주세요.\n\n"
  +"· 쓰는 곳: 두두 그림을 화면 맨 위에 그리고, 두두 그림 위의 작은 영역에서만 터치를 받아요.\n"
  +"· 쓰지 않는 것: 다른 앱의 화면·글자 읽기, 전체 터치 수집, 대신 누르기. 아무것도 저장하거나 보내지 않아요.\n\n"
  +"켜는 방법: 설정 열기 → 설치된 앱(또는 다운로드한 앱) → 두두 → 사용 켜기.\n\n"
  +"\"제한된 설정\" 안내가 나오면(Android 13 이상, 직접 설치한 앱): 앱 정보 열기 → 오른쪽 위 ⋮ → \"제한된 설정 허용\" 후 다시 켜 주세요.\n\n"
  +"완전히 끄려면 같은 접근성 화면에서 두두를 끄면 돼요.";
 void permissionGuide(){AlertDialog d=new AlertDialog.Builder(this).setTitle("권한 안내").setMessage(PERMISSION_TEXT).setPositiveButton("접근성 설정 열기",(v,w)->openAccessibility()).setNeutralButton("앱 정보 열기",(v,w)->{try{startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.fromParts("package",getPackageName(),null)));}catch(ActivityNotFoundException e){Toast.makeText(this,"앱 정보 화면을 열 수 없어요.",Toast.LENGTH_SHORT).show();}}).setNegativeButton("닫기",null).create();d.setOnShowListener(v->AppUi.fonts(this,d.getWindow().getDecorView()));d.show();}
 void openAccessibility(){try{startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));}catch(ActivityNotFoundException e){Toast.makeText(this,"접근성 설정을 열 수 없어요.",Toast.LENGTH_SHORT).show();}}
 void licenses(){String font;try(java.io.InputStream in=getAssets().open("licenses/maplestory.txt")){java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();byte[] bytes=new byte[4096];int n;while((n=in.read(bytes))!=-1)out.write(bytes,0,n);font=out.toString("UTF-8");}catch(Exception e){font="메이플스토리 서체의 지적 재산권을 포함한 모든 권리는 ㈜넥슨코리아에 있습니다.";}
  notice("글꼴·이용 고지","[팬메이드 앱 안내]\n두두는 게임 「트릭컬」의 캐릭터를 바탕으로 그린 팬아트로 만든 비공식·비상업 팬메이드 앱이에요. 무료로 배포하며 판매하거나 광고를 넣지 않아요. 원작 캐릭터와 게임에 대한 권리는 원저작권자에게 있어요.\n\n[글꼴]\n이 앱에는 넥슨코리아가 제공한 메이플스토리 서체(Bold·Light)가 적용되어 있어요.\n\n"+font);}
 void execute(){if(!foregroundOwner())return;pendingStart=true;waitingForPermission=false;if(!allowed()){AlertDialog d=new AlertDialog.Builder(this).setTitle("두두 표시 허용").setMessage("접근성 설정에서 두두를 켜 주세요. 두두 그림과 두두 위의 작은 터치 영역에만 사용하며 다른 앱의 내용은 읽지 않아요.\n\n자세한 내용은 \"권한 안내\"를 눌러 보세요.").setPositiveButton("설정 열기",(v,w)->{waitingForPermission=true;openAccessibility();}).setNegativeButton("나중에",(v,w)->{pendingStart=false;waitingForPermission=false;}).create();d.setOnCancelListener(v->{pendingStart=false;waitingForPermission=false;});d.setOnShowListener(v->AppUi.fonts(this,d.getWindow().getDecorView()));d.show();return;}startIfReady();}
 void startIfReady(){if(!foregroundOwner()||!pendingStart||!allowed())return;PetOverlayService s=PetOverlayService.current;if(s==null){state.setText("표시 연결을 준비하고 있어요.");return;}s.startSession();if(!s.running)return;pendingStart=false;waitingForPermission=false;startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME));}
 void refresh(){if(state==null)return;PetOverlayService s=PetOverlayService.current;state.setText(s!=null&&s.running?"두두가 화면에 나와 있어요.":allowed()?"준비됐어요. 실행을 눌러 주세요.":"처음 한 번 표시 권한을 허용해 주세요.");showGlow();}
 protected void onResume(){super.onResume();visible=true;resumed=true;foreground=new WeakReference<>(this);if(waitingForPermission&&!allowed())pendingStart=false;waitingForPermission=false;if(PetOverlayService.current!=null)PetOverlayService.current.visibility();refresh();startIfReady();}
 protected void onPause(){resumed=false;if(!waitingForPermission)pendingStart=false;if(foreground.get()==this){foreground.clear();visible=false;}if(PetOverlayService.current!=null)PetOverlayService.current.visibility();super.onPause();}
 protected void onDestroy(){pendingStart=false;waitingForPermission=false;if(foreground.get()==this){foreground.clear();visible=false;}updates.close();super.onDestroy();}
 public void onConfigurationChanged(Configuration c){super.onConfigurationChanged(c);showGlow();}
}
