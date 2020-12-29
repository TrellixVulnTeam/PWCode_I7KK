[Net.ServicePointManager]::SecurityProtocol = "tls12, tls11, tls"
$tmpDir = [IO.Path]::Combine($Env:USERPROFILE, 'appdata\local\temp')
$windowsDir = (get-item $PSScriptRoot).FullName
$vendorDir = (get-item $windowsDir).parent.FullName

# Download wimlib:
If (-Not (Test-Path "$windowsDir\wimlib\wimlib-imagex.exe")) {
    $url= "https://wimlib.net/downloads/wimlib-1.13.1-windows-x86_64-bin.zip"
    $filename = [System.IO.Path]::GetFileName($url);
    Write-Host "Downloading $filename "
    Invoke-WebRequest -Uri $url -OutFile "$tmpDir\$filename"
    Write-Host "Extracting $filename to $windowsDir"
    Expand-Archive "$tmpDir\$filename" -DestinationPath "$windowsDir\wimlib"
}

# Download python:
If (-Not (Test-Path "$windowsDir\python\python.exe")) {
    $url= "https://github.com/Preservation-Workbench/windows_deps/releases/download/v0.1/python-3.8.5-embed-amd64.zip"
    $filename = [System.IO.Path]::GetFileName($url);
    Write-Host "Downloading $filename "
    Invoke-WebRequest -Uri $url -OutFile "$tmpDir\$filename"
    Write-Host "Extracting $filename to $windowsDir"
    Expand-Archive "$tmpDir\$filename" -DestinationPath "$windowsDir\python"
}

# Download JRE:
If (-Not (Test-Path "$windowsDir\jre\bin\java.exe")) {
    $url= "https://github.com/Preservation-Workbench/windows_deps/releases/download/v0.1/jre.zip"
    $filename = [System.IO.Path]::GetFileName($url);
    Write-Host "Downloading $filename "
    Invoke-WebRequest -Uri $url -OutFile "$tmpDir\$filename"
    Write-Host "Extracting $filename to $windowsDir"
    Expand-Archive "$tmpDir\$filename" -DestinationPath "$windowsDir\jre"
}

#wget https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar -O ojdbc10.jar
If (-Not (Test-Path "$vendorDir\jars\ojdbc10.jar")) {
	$url= "https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar"
    $fileName = [System.IO.Path]::GetFileName($url)
    New-Item -ItemType Directory -Force -Path "$vendorDir\jdbc"
    Write-Host "Downloading $fileName..."
    Invoke-WebRequest -Uri $url -OutFile "$vendorDir\jdbc\ojdbc10.jar"
}

Write-Host "All dependencies installed."
