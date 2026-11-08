"""공개 배포 서명(ODD FACTORY 공개 키)으로 두두 릴리스 APK를 만든다. 사용자가 직접 실행한다.
  python android\\tools\\sign_public.py
- 입력: android/dist/oddfactory-dudu-vc<code>-sdk<min>.apk (gradlew distApk 결과, 개발용 서명)
- 출력: android/dist/release/oddfactory-dudu-vc<code>-sdk<min>.apk (공개 키 서명, GitHub Release에 첨부할 파일)
- 공용 서명 도구(_release-prep .../package_apks.py)와 D: 백업의 공개 키를 그대로 쓴다. 비밀번호는 화면에 출력하지 않는다."""
import os, re, sys, zipfile, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(r"C:\Users\ehdrh\Desktop\프로젝트\_release-prep-20261031\performance-resume-r1\drive-update-r1")
BACKUP = Path("D:/OddFactory-Signing-Backup-20261107")
os.environ["JAVA_HOME"] = r"C:\Program Files\Android\Android Studio\jbr"   # 시스템 JAVA_HOME(JDK 11)은 공개 키(PKCS12 HmacPBESHA256)를 못 읽음 → Java 17+ 사용
sys.path.insert(0, str(TOOLS))
from package_apks import sign, verify_signature, digest, run, SDK  # noqa: E402

gradle = (ROOT / "app" / "build.gradle").read_text(encoding="utf-8")
code = int(re.search(r"versionCode (\d+)", gradle)[1]); name = re.search(r"versionName '([^']+)'", gradle)[1]
minimum = int(re.search(r"minSdk (\d+)", gradle)[1])
file = f"oddfactory-dudu-vc{code}-sdk{minimum}.apk"
src = ROOT / "dist" / file
assert src.exists(), f"먼저 gradlew distApk 로 {file} 를 만드세요"
out_dir = ROOT / "dist" / "release"; out_dir.mkdir(exist_ok=True)
work = out_dir / "work"; work.mkdir(exist_ok=True)

unsigned = work / "unsigned.apk"   # 개발용 서명 제거
with zipfile.ZipFile(src) as a, zipfile.ZipFile(unsigned, "w") as b:
    for i in a.infolist():
        if re.match(r"META-INF/[^/]+\.(SF|RSA|EC|DSA|MF)$", i.filename): continue
        b.writestr(i, a.read(i.filename), compress_type=i.compress_type)
aligned = work / "aligned.apk"
run(SDK / "zipalign.exe", "-f", "-P", "16", "4", unsigned.name, aligned.name, cwd=work)
env = dict(os.environ, ODDFACTORY_PUBLIC_SIGN_SECRET=(BACKUP / "recovery-password.txt").read_text(encoding="ascii"))
output = out_dir / file
sign(aligned, output, minimum, BACKUP / "oddfactory-public.p12", env)
verify_signature(output, digest(BACKUP / "release-certificate.der"))
badging = run(SDK / "aapt.exe", "dump", "badging", output.name, cwd=out_dir)
assert f"versionCode='{code}'" in badging and f"versionName='{name}'" in badging and "application-debuggable" not in badging
print("OK", name, file, "sha256:", hashlib.sha256(output.read_bytes()).hexdigest())
print("GitHub Release 태그:", "v" + name)
