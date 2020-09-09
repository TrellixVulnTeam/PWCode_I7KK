function Get-RedirectedUrl
{
    Param (
        [Parameter(Mandatory=$true)]
        [String]$URL
    )

    $request = [System.Net.WebRequest]::Create($url)
    $request.AllowAutoRedirect=$false
    $response=$request.GetResponse()

    If ($response.StatusCode -eq "Found")
    {
        $response.GetResponseHeader("Location")
    }
}

[Net.ServicePointManager]::SecurityProtocol = "tls12, tls11, tls"
$tmpDir = [IO.Path]::Combine($Env:USERPROFILE, 'appdata\local\temp') 
$windowsDir = (get-item $PSScriptRoot).FullName
$vendorDir = (get-item $windowsDir).parent.FullName
$pythonDir = [IO.Path]::Combine($windowsDir, 'python')
$jreDir = [IO.Path]::Combine($windowsDir, 'jre')
$jdbcDir = [IO.Path]::Combine($vendorDir, 'jdbc')

# Download SQL Workbench J
# $wbTestPath = [IO.Path]::Combine($binPath, 'sqlworkbench.jar')
# If (-Not (Test-Path $wbTestPath)) {
# 	$url= "https://www.sql-workbench.eu/Workbench-Build125.zip"
# 	$filename = [System.IO.Path]::GetFileName($url); 
# 	Write-Host "Downloading $filename (approx. 6MB)"
# 	Invoke-WebRequest -Uri $url -OutFile $filename
# 	Write-Host "Extracting $filename  to $binPath"
# 	Expand-Archive $filename -DestinationPath $binPath
# }

# Download Python
$pythonPath = [IO.Path]::Combine($pythonDir, 'python.exe')
If (-Not (Test-Path $pythonPath)) {
	$url= "https://www.python.org/ftp/python/3.8.5/python-3.8.5-embed-amd64.zip"
	New-Item -ItemType Directory -Force -Path $pythonDir 
    $filename = [System.IO.Path]::GetFileName($url); 
    Write-Host "Downloading $filename"
    #$zipFilePath = [IO.Path]::Combine($tmpDir, 'python.zip') 
    #Invoke-WebRequest -Uri $url -OutFile $zipFilePath
    # Test med modifisert embedded python:
    $zipFilePath = "D:\python-3.8.5-embed-amd64.zip"
    Copy-Item -Path $zipFilePath -Destination $pythonDir -Force
    Write-Host "Extracting $zipFilePath to $pythonDir"
    Expand-Archive $zipFilePath -DestinationPath $pythonDir
    #Fix python path
    $pthFile = [IO.Path]::Combine($pythonDir, 'python38._pth')
    # (Get-Content $pthFile) -replace "#import site", 'import site' | Set-Content $pthFile
    # (Get-Content $pthFile) -replace "python", 'Lib\site-packages\python' | Set-Content $pthFile
    $text = [string]::Join("`n", (Get-Content $pthFile))
    [regex]::Replace($text, "\.`n", ".`nLib\site-packages`n..\..\..\`n", "Singleline") | Set-Content $pthFile
}

#Start-Process -NoNewWindow -FilePath $pythonPath -ArgumentList "-m pip install --no-warn-script-location --force-reinstall JPype1==0.7.1 psutil jaydebeapi toposort flake8 autopep8 rope beautifulsoup4 lxml pygments petl wand ocrmypdf img2pdf pdfy"

# $getPipPath = [IO.Path]::Combine($pythonDir, 'get-pip.py')
# if(-not (Test-Path $getPipPath)) {
#     $url = "https://bootstrap.pypa.io/get-pip.py"
#     $output = $getPipPath
#     Invoke-WebRequest -Uri $url -OutFile $output
#     & $pythonPath $getPipPath
#     #$pipPath = [IO.Path]::Combine($pythonDir, 'Scripts', 'pip.exe')
#     Start-Process -NoNewWindow -FilePath $pythonPath -ArgumentList "-m pip install --no-warn-script-location --force-reinstall JPype1 psutil jaydebeapi toposort flake8 autopep8 rope beautifulsoup4 lxml pygments"
#     #Start-Process -NoNewWindow -FilePath $pythonPath -ArgumentList "-m pip install --no-warn-script-location --force-reinstall JPype1==0.6.3 psutil jaydebeapi toposort flake8 autopep8 rope beautifulsoup4 lxml pygments petl wand ocrmypdf img2pdf pdfy"
#     #ExecutePython($"-m pip install -r {_requirementsFile} --no-warn-script-location");
#     # Write-Host "Python modules installed."
#     # TODO: Legg inn sjekk mot denne tilsv. som gjort i linux script? Evt. fjerne i begge?
#     $pipDonePath = [IO.Path]::Combine($pythonDir, 'pip_done')
#     New-Item $pipDonePath -type file
# }


# Download wimlib
# $wimlibTestPath = [IO.Path]::Combine($binPath, 'PWB','wimlib-imagex.exe')
# If (-Not (Test-Path $wimlibTestPath)) {
#     $url= "https://wimlib.net/downloads/wimlib-1.13.1-windows-x86_64-bin.zip"
#     $filename = [System.IO.Path]::GetFileName($url); 
#     Write-Host "Downloading $filename (approx. 1MB)"
#     Invoke-WebRequest -Uri $url -OutFile $filename
#     Write-Host "Extracting $filename  to $binPath"
#     Expand-Archive $filename -DestinationPath $PSScriptRoot
# }

# cd amazon-corretto-*-linux-x64/bin/
# ./jlink --output $SCRIPTPATH/vendor/linux/jre --compress=2 --no-header-files --no-man-pages --module-path ../jmods --add-modules java.base,java.datatransfer,java.desktop,java.management,java.net.http,java.security.jgss,java.sql,java.sql.rowset,java.xml,jdk.net,jdk.unsupported,jdk.unsupported.desktop,jdk.xml.dom
# rm $SCRIPTPATH/vendor/linux/amazon-corretto-11-x64-linux-jdk.tar.gz
# rm -rdf $SCRIPTPATH/vendor/linux/amazon-corretto-*-linux-x64

# %userprofile%\AppData\Local\Temp
# "C:\Users\$($_.name)\appdata\local\temp"

#Download JRE
$jreTestPath = [IO.Path]::Combine($jreDir, 'bin', 'javaw.exe')
If (-Not (Test-Path $jreTestPath)) {
    $url= "https://corretto.aws/downloads/latest/amazon-corretto-11-x64-windows-jdk.zip"
    $fileName = [System.IO.Path]::GetFileName($url)
    # $filepath = [IO.Path]::Combine((get-item $binPath).parent.parent.FullName, 'tmp', 'jre.zip') 
    $zipFilePath = [IO.Path]::Combine($tmpDir, 'jre.zip') 

    If (-Not (Test-Path $zipFilePath)) {
        Write-Host "Downloading $fileName..."
        Invoke-WebRequest -Uri $url -OutFile $zipFilePath
    }

    $jreTmpDir = [IO.Path]::Combine($tmpDir, 'jre') 
    If (Test-Path $jreTmpDir) {
        Remove-Item -path $jreTmpDir -recurse
    }
    Set-Location -Path $tmpDir
    Write-Host "Extracting zipped JDK..."
    Expand-Archive $zipFilePath  
    
    Write-Host "Generating optimized Java runtime..."
    $jreSubDir = Get-ChildItem -Directory -Path $jreTmpDir | Select-Object -ExpandProperty FullName
    #$jreTmpDir = [IO.Path]::Combine($jreTmpDir, $jreSubDir) 
    $jlinkPath = [IO.Path]::Combine($jreTmpDir, $jreSubDir, 'bin', 'jlink.exe') 
    #Write-Host $jreDir
    # variabel for jmods?
    Start-Process -NoNewWindow -FilePath $jlinkPath -ArgumentList "--output $jreDir --compress=2 --no-header-files --no-man-pages --module-path ..\jmods --add-modules java.base,java.datatransfer,java.desktop,java.management,java.net.http,java.security.jgss,java.sql,java.sql.rowset,java.xml,jdk.net,jdk.unsupported,jdk.unsupported.desktop,jdk.xml.dom"
    # Write-Host $jlinkPath
    #Expand-Archive $filepath -DestinationPath $jreDir
    # $jdkDir = Get-ChildItem -Directory -Path $jreDir | Select-Object -ExpandProperty FullName
    # Get-ChildItem -Path $jdkDir | Copy-Item -Recurse  -Destination $jreDir -Container
} 

#wget https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar -O ojdbc10.jar
$jdbcPath = [IO.Path]::Combine($jdbcDir, 'ojdbc10.jar')
If (-Not (Test-Path $jdbcPath)) {
	$url= "https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc10/19.6.0.0/ojdbc10-19.6.0.0.jar"
    New-Item -ItemType Directory -Force -Path $jdbcDir 
    $fileName = [System.IO.Path]::GetFileName($url)
    Write-Host "Downloading $fileName..."
    Invoke-WebRequest -Uri $url -OutFile $jdbcPath
}

#OJDBC10=$SCRIPTPATH/vendor/jdbc/ojdbc10.jar

#Cleanup
# Get-ChildItem -Path $PSScriptRoot -exclude appJar | Where-Object{ $_.PSIsContainer } | ForEach-Object { Remove-Item -Path $_.FullName -Recurse -Force -Confirm:$false}
# Get-ChildItem -Path $PSScriptRoot\* -include *.txt,*.cmd | ForEach-Object { Remove-Item -Path $_.FullName }
# Get-ChildItem -Path $binPath\* -include *.ps1,*.cmd,*.sample,*.sh,*-sample.xml,*.vbs,*.exe,*.zip,*.pdf | ForEach-Object { Remove-Item -Path $_.FullName }
# $pythonExe = [IO.Path]::Combine($pythonDir, 'python.exe')
# If (Test-Path $pythonExe) {Rename-Item -Path $pythonExe -NewName "python3.exe"}

