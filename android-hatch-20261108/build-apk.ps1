[CmdletBinding()]
param(
    [string]$Sdk = "$env:LOCALAPPDATA/Android/Sdk",
    [string]$Java = 'C:/Program Files/Android/Android Studio/jbr'
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$bt=Join-Path $Sdk 'build-tools/36.0.0'
$platform=Join-Path $Sdk 'platforms/android-35/android.jar'
$work=Join-Path $root 'build'
$classes=Join-Path $work 'classes'
$dex=Join-Path $work 'dex'
$res=Join-Path $root 'res'
New-Item -ItemType Directory -Force -Path $work,$classes,$dex | Out-Null
$env:JAVA_HOME=$Java
function Run($binary,[string[]]$arguments){
    & $binary @arguments
    if($LASTEXITCODE -ne 0){throw "$binary failed with exit $LASTEXITCODE"}
}
Run "$Java/bin/javac.exe" @('--release','8','-encoding','UTF-8','-cp',$platform,'-d',$classes,"$root/src/HatchActivity.java")
Run "$Java/bin/jar.exe" @('cf',"$work/classes.jar",'-C',$classes,'.')
Run "$bt/d8.bat" @('--min-api','23','--lib',$platform,'--output',$dex,"$work/classes.jar")
Run "$bt/aapt2.exe" @('compile','--dir',$res,'-o',"$work/res.zip")
Run "$bt/aapt2.exe" @('link','-o',"$work/unsigned.apk",'-I',$platform,'--manifest',"$root/AndroidManifest.xml",'-A',"$root/assets","$work/res.zip")
Run "$Java/bin/jar.exe" @('uf',"$work/unsigned.apk",'-C',$dex,'classes.dex')
Run "$bt/zipalign.exe" @('-f','4',"$work/unsigned.apk","$work/aligned.apk")
$keystore=Join-Path $work 'hatch-demo-debug.jks'
if(!(Test-Path -LiteralPath $keystore)){
    Run "$Java/bin/keytool.exe" @('-genkeypair','-keystore',$keystore,'-storepass','android','-keypass','android','-alias','androiddebugkey','-dname','CN=Dudu Hatch Debug,O=ODD FACTORY,C=KR','-keyalg','RSA','-keysize','2048','-validity','3650')
}
$apk=Join-Path $root 'dudu-hatch-preview.apk'
Run "$bt/apksigner.bat" @('sign','--ks',$keystore,'--ks-key-alias','androiddebugkey','--ks-pass','pass:android','--key-pass','pass:android','--out',$apk,"$work/aligned.apk")
Run "$bt/apksigner.bat" @('verify',$apk)
Get-Item -LiteralPath $apk | Select-Object FullName,Length
