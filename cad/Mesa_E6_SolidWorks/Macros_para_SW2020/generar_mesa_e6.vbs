'  Ejecutar: cscript //nologo generar_mesa_e6.vbs "C:\carpeta\salida"
' =====================================================================
'  Mesa de trabajo + kit de obstaculos para Dobot Magician E6
'  Generador de piezas nativas SOLIDWORKS (compatible 2020 o superior)
'  Unidades del modelo: mm (la API trabaja en metros; MM convierte)
'  Ejes SOLIDWORKS: X = largo de la mesa, Y = vertical, Z = fondo.
'  Origen de la mesa = eje J1 del robot sobre la superficie del tablero.
'  Origen de cada obstaculo = centro de su cara inferior (agujero de montaje).
' =====================================================================
Dim swApp, doc, skm, fm, ext, lg, outDir, nOk, nFail
Const MM = 0.001
Const PI = 3.14159265358979

Sub WLog(s)
  On Error Resume Next
  lg.WriteLine s
End Sub

Sub NewPart()
  On Error Resume Next
  Set doc = swApp.NewDocument(swApp.GetUserPreferenceStringValue(8), 0, 0, 0)
  Set skm = doc.SketchManager
  Set fm = doc.FeatureManager
  Set ext = doc.Extension
  ext.SetUserPreferenceInteger 263, 0, 5      ' sistema de unidades MMGS
  If ext.GetUserPreferenceInteger(263, 0) <> 5 Then WLog "   aviso: no se pudo fijar MMGS"

  skm.AddToDB = True
  skm.DisplayWhenAdded = False
End Sub

Function GetPlane(idx)          ' 0 = Alzado/Front, 1 = Planta/Top, 2 = Vista lateral/Right
  On Error Resume Next
  Dim f, n
  n = 0
  Set f = doc.FirstFeature
  Do While Not f Is Nothing
    If f.GetTypeName2 = "RefPlane" Then
      If n = idx Then
        Set GetPlane = f
        Exit Function
      End If
      n = n + 1
    End If
    Set f = f.GetNextFeature
  Loop
End Function

Sub OpenSketch(pl)
  On Error Resume Next
  doc.ClearSelection2 True
  pl.Select2 False, 0
  skm.InsertSketch True
End Sub

Sub CloseSketch(nm, fullDef)
  On Error Resume Next
  Dim f, r
  If fullDef Then
    r = skm.FullyDefineSketch(True, True, 1023, True, 1, Nothing, 1, Nothing, -1, -1)
    If Err.Number <> 0 Or r <> 0 Then WLog "   definir croquis " & nm & ": r=" & r & " " & Err.Description
    Err.Clear
  End If
  skm.InsertSketch True
  Set f = doc.FeatureByPositionReverse(0)
  f.Name = nm
  doc.ClearSelection2 True
  f.Select2 False, 0
End Sub

Sub Check(f, nm)
  On Error Resume Next
  Dim bad
  bad = True
  If IsObject(f) Then bad = (f Is Nothing)
  If bad Then
    nFail = nFail + 1
    WLog "   FALLO: " & nm
  Else
    f.Name = nm
    nOk = nOk + 1
  End If
  doc.ClearSelection2 True
End Sub

' --- entidades de croquis (coordenadas en mm) ---
Sub Rect(cx, cy, w, h)
  On Error Resume Next
  skm.CreateCenterRectangle cx * MM, cy * MM, 0, (cx + w / 2) * MM, (cy + h / 2) * MM, 0
End Sub

Sub Circ(cx, cy, d)
  On Error Resume Next
  skm.CreateCircleByRadius cx * MM, cy * MM, 0, d / 2 * MM
End Sub

Sub Poly(p)           ' p = Array(x0,y0, x1,y1, ...) contorno cerrado
  On Error Resume Next
  Dim i, n
  n = (UBound(p) + 1) / 2
  For i = 0 To n - 1
    skm.CreateLine p(2 * i) * MM, p(2 * i + 1) * MM, 0, p(2 * ((i + 1) Mod n)) * MM, p(2 * ((i + 1) Mod n) + 1) * MM, 0
  Next
End Sub

Sub Lin(x1, y1, x2, y2)
  On Error Resume Next
  skm.CreateLine x1 * MM, y1 * MM, 0, x2 * MM, y2 * MM, 0
End Sub

' --- operaciones ---
Sub Extrude(nm, depth, rev)                ' saliente blind desde el plano del croquis
  On Error Resume Next
  Dim f
  Set f = fm.FeatureExtrusion3(True, False, rev, 0, 0, depth * MM, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  Check f, nm
End Sub

Sub ExtrudeMid(nm, depth)                  ' saliente plano medio
  On Error Resume Next
  Dim f
  Set f = fm.FeatureExtrusion3(True, False, False, 6, 0, depth * MM, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)
  Check f, nm
End Sub

Sub CutBlind(nm, depth, rev)
  On Error Resume Next
  Dim f
  Set f = fm.FeatureCut4(True, False, rev, 0, 0, depth * MM, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
  Check f, nm
End Sub

Sub CutThruBoth(nm)
  On Error Resume Next
  Dim f
  Set f = fm.FeatureCut4(False, False, False, 1, 1, 0.01, 0.01, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False, False)
  Check f, nm
End Sub

Sub Revolve(nm)
  On Error Resume Next
  Dim f
  Set f = fm.FeatureRevolve2(True, True, False, False, False, False, 0, 0, 2 * PI, 0, False, False, 0, 0, 0, 0, 0, True, True, True)
  Check f, nm
End Sub

' agujeros ciegos de montaje desde la cara inferior (plano Planta, hacia +Y)
Sub MountHoles(xs, d, depth)
  On Error Resume Next
  Dim i
  OpenSketch GetPlane(1)
  For i = 0 To UBound(xs)
    Circ xs(i), 0, d
  Next
  CloseSketch "Croquis_agujeros_montaje", True
  CutBlind "Agujero_inserto_M6", depth, True
End Sub

Sub Prop(nm, v)
  On Error Resume Next
  ext.CustomPropertyManager("").Add3 nm, 30, v, 1
End Sub

Sub SavePart(fname, desc)
  On Error Resume Next
  Dim r, b
  Prop "Descripcion", desc
  Prop "Proyecto", "Mesa RL Dobot Magician E6"
  doc.ForceRebuild3 False
  doc.ShowNamedView2 "*Isometric", 7
  doc.ViewZoomtofit2
  r = doc.SaveAs3(outDir & "\" & fname & ".SLDPRT", 0, 1)
  doc.SaveAs3 outDir & "\STEP\" & fname & ".STEP", 0, 1

  WLog fname & "  guardado=" & (r = 0)
End Sub

Sub CloseDoc()
  On Error Resume Next
  swApp.CloseDoc doc.GetTitle
End Sub

' =====================================================================
'  MESA DE TRABAJO
' =====================================================================
Sub BuildTable()
  On Error Resume Next
  Dim i, j, cx, cy, brd, crn, rob, n

  NewPart
  OpenSketch GetPlane(1)
  Rect 0, 0, 1200, 1000
  CloseSketch "Croquis_tablero", True
  Extrude "Tablero_1200x1000x25", 25, True
  OpenSketch GetPlane(1)
  n = 0
  For i = 0 To 23
    For j = 0 To 19
      cx = -575 + 50 * i
      cy = -475 + 50 * j
      brd = (i = 0 Or i = 23 Or j = 0 Or j = 19)
      crn = ((i <= 1 Or i >= 22) And (j <= 1 Or j >= 18))
      rob = (Abs(cx) < 100 And Abs(cy) < 100)
      If Not (brd Or crn Or rob) Then
        Circ cx, cy, 6.6
        n = n + 1
      End If
    Next
  Next
  CloseSketch "Croquis_rejilla_M6_paso50", False
  CutThruBoth "Rejilla_agujeros_M6_D6.6"
  WLog "   agujeros rejilla: " & n
  SavePart "MESA_01_Tablero", "Tablero 1200x1000x25 con rejilla M6 paso 50 mm; origen = eje J1 del robot"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 70, 70: CloseSketch "Croquis_pata", True
  Extrude "Pata_70x70x725", 725, False
  SavePart "MESA_02_Pata", "Pata 70x70x725 (x4)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 1060, 25: CloseSketch "Croquis_faldon", True
  Extrude "Faldon_largo", 80, False
  SavePart "MESA_03_Faldon_largo", "Faldon largo 1060x25x80 (x2)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 25, 860: CloseSketch "Croquis_faldon", True
  Extrude "Faldon_corto", 80, False
  SavePart "MESA_04_Faldon_corto", "Faldon corto 25x860x80 (x2)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 1060, 25: CloseSketch "Croquis_travesano", True
  Extrude "Travesano_largo", 40, False
  SavePart "MESA_05_Travesano_largo", "Travesano inferior largo 1060x25x40 (x2)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 25, 860: CloseSketch "Croquis_travesano", True
  Extrude "Travesano_corto", 40, False
  SavePart "MESA_06_Travesano_corto", "Travesano inferior corto 25x860x40 (x2)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 1060, 980: CloseSketch "Croquis_repisa", True
  Extrude "Repisa_1060x980x18", 18, False
  SavePart "MESA_07_Repisa", "Repisa inferior 1060x980x18"
  CloseDoc
End Sub

' =====================================================================
'  OBSTACULOS
' =====================================================================
Sub BuildObstacles()
  On Error Resume Next
  Dim f

  ' ---------- prismaticas ----------
  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 75, 75: CloseSketch "Croquis_base", True
  Extrude "Cubo_75", 75, False
  MountHoles Array(0), 8, 14
  SavePart "P01_Cubo_75", "Cubo 75x75x75"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 75, 75: CloseSketch "Croquis_base", True
  Extrude "Columna_75x150", 150, False
  MountHoles Array(0), 8, 14
  doc.ClearSelection2 True
  GetPlane(1).Select2 False, 0
  Set f = fm.InsertRefPlane(8, 150 * MM, 0, 0, 0, 0)
  Check f, "Plano_cara_superior"
  OpenSketch f: Circ 0, 0, 8: CloseSketch "Croquis_agujero_superior", True
  CutBlind "Agujero_superior_M6", 14, False
  SavePart "P02_Columna_75x150", "Columna 75x75x150; inserto M6 arriba y abajo (pilar del portal)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 125, 75: CloseSketch "Croquis_base", True
  Extrude "Caja_baja", 50, False
  MountHoles Array(-50, 50), 8, 14
  SavePart "P03_Caja_baja_125x75x50", "Caja baja 125x75x50"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 175, 25: CloseSketch "Croquis_base", True
  Extrude "Muro", 150, False
  MountHoles Array(-50, 50), 8, 14
  SavePart "P04_Muro_175x25x150", "Muro delgado 175x25x150"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  Poly Array(-62.5, 0, 62.5, 0, 62.5, 150, 37.5, 150, 37.5, 20, -62.5, 20)
  CloseSketch "Croquis_perfil_L", True
  ExtrudeMid "Angulo_L", 75
  MountHoles Array(-50, 0), 10, 14
  SavePart "P05_Angulo_L_125x75x150", "Angulo L: ala 20 mm, alma 25x75x150"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  Poly Array(-87.5, 0, 87.5, 0, 87.5, 120, 12.5, 120, 12.5, 80, -37.5, 80, -37.5, 40, -87.5, 40)
  CloseSketch "Croquis_perfil_escalera", True
  ExtrudeMid "Escalera", 75
  MountHoles Array(-50, 50), 8, 14
  SavePart "P06_Escalera_175x75", "Escalera de 3 escalones 40/80/120"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1)
  Poly Array(-62.5, -12.5, -12.5, -12.5, -12.5, -62.5, 12.5, -62.5, 12.5, -12.5, 62.5, -12.5, 62.5, 12.5, 12.5, 12.5, 12.5, 62.5, -12.5, 62.5, -12.5, 12.5, -62.5, 12.5)
  CloseSketch "Croquis_cruz", True
  Extrude "Cruz", 100, False
  MountHoles Array(-50, 0, 50), 8, 14
  SavePart "P07_Cruz_125x125x100", "Cruz en planta 125x125, brazos 25, alto 100"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 275, 75: CloseSketch "Croquis_viga", True
  Extrude "Viga", 20, False
  OpenSketch GetPlane(1): Circ -100, 0, 6.6: Circ 100, 0, 6.6: CloseSketch "Croquis_pasantes", True
  CutThruBoth "Pasantes_M6"
  SavePart "P08_Viga_portal_275x75x20", "Viga de portal; une 2 columnas P02 a 200 mm entre centros"
  CloseDoc

  ' ---------- revolucion ----------
  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.1, 0
  Poly Array(0, 0, 30, 0, 30, 100, 0, 100)
  CloseSketch "Croquis_perfil", True
  Revolve "Cilindro_D60x100"
  MountHoles Array(0), 8, 14
  SavePart "R01_Cilindro_D60x100", "Cilindro D60 x 100"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.22, 0
  Poly Array(0, 0, 15, 0, 15, 220, 0, 220)
  CloseSketch "Croquis_perfil", True
  Revolve "Poste_D30x220"
  MountHoles Array(0), 8, 14
  SavePart "R02_Poste_D30x220", "Poste esbelto D30 x 220"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.12, 0
  Poly Array(0, 0, 50, 0, 0, 120)
  CloseSketch "Croquis_perfil", True
  Revolve "Cono_D100x120"
  MountHoles Array(0), 8, 14
  SavePart "R03_Cono_D100x120", "Cono D100 x 120"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.1, 0
  Poly Array(0, 0, 50, 0, 20, 100, 0, 100)
  CloseSketch "Croquis_perfil", True
  Revolve "Tronco_cono"
  MountHoles Array(0), 8, 14
  SavePart "R04_Tronco_cono_D100_D40x100", "Tronco de cono D100 a D40 x 100"
  CloseDoc

  Dim ys
  ys = 120 - Sqr(50 * 50 - 12 * 12)
  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.17, 0
  Lin 0, 0, 30, 0
  Lin 30, 0, 30, 8
  Lin 30, 8, 12, 8
  Lin 12, 8, 12, ys
  skm.CreateArc 0, 120 * MM, 0, 12 * MM, ys * MM, 0, 0, 170 * MM, 0, 1
  Lin 0, 170, 0, 0
  CloseSketch "Croquis_perfil", True
  Revolve "Esfera_pedestal"
  MountHoles Array(0), 8, 14
  SavePart "R05_Esfera_D100_pedestal", "Esfera D100 sobre pedestal (base D60x8, cuello D24); centro a 120 mm"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.06, 0
  Lin 0, 0, 60, 0
  skm.CreateArc 0, 0, 0, 60 * MM, 0, 0, 0, 60 * MM, 0, 1
  Lin 0, 60, 0, 0
  CloseSketch "Croquis_perfil", True
  Revolve "Domo_D120"
  MountHoles Array(0), 8, 14
  SavePart "R06_Domo_D120", "Domo semiesferico D120 (alto 60)"
  CloseDoc

  ' ---------- prismas poligonales y piramide ----------
  NewPart
  OpenSketch GetPlane(1)
  skm.CreatePolygon 0, 0, 0, 40 * MM, 0, 0, 6, False
  CloseSketch "Croquis_hexagono", True
  Extrude "Prisma_hexagonal", 120, False
  MountHoles Array(0), 8, 14
  SavePart "R07_Prisma_hexagonal_80x120", "Prisma hexagonal, 80 entre vertices x 120"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1)
  skm.CreatePolygon 0, 0, 0, 0, 50 * MM, 0, 3, False
  CloseSketch "Croquis_triangulo", True
  Extrude "Prisma_triangular", 100, False
  MountHoles Array(0), 8, 14
  SavePart "R08_Prisma_triangular_100x100", "Prisma triangular, circunradio 50 x 100"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  Poly Array(-50, 0, 50, 0, 0, 120)
  CloseSketch "Croquis_triangulo_frontal", True
  ExtrudeMid "Cuna", 100
  OpenSketch GetPlane(2)
  Poly Array(-60, 0, -50, 0, 0, 120, 50, 0, 60, 0, 60, 130, -60, 130)
  CloseSketch "Croquis_recorte_lateral", True
  CutThruBoth "Recorte_caras_piramide"
  MountHoles Array(0), 8, 14
  SavePart "R09_Piramide_cuadrada_100x120", "Piramide de base cuadrada 100x100 x 120"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 175, 25: CloseSketch "Croquis_base", True
  Extrude "Muro_alto", 350, False
  MountHoles Array(-50, 50), 8, 14
  SavePart "T01_Muro_alto_175x25x350", "Muro alto 175x25x350"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 75, 75: CloseSketch "Croquis_base", True
  Extrude "Columna_alta_75x350", 350, False
  MountHoles Array(0), 8, 14
  doc.ClearSelection2 True
  GetPlane(1).Select2 False, 0
  Set f = fm.InsertRefPlane(8, 350 * MM, 0, 0, 0, 0)
  Check f, "Plano_cara_superior"
  OpenSketch f: Circ 0, 0, 8: CloseSketch "Croquis_agujero_superior", True
  CutBlind "Agujero_superior_M6", 14, False
  SavePart "T02_Columna_alta_75x75x350", "Columna alta 75x75x350; inserto M6 arriba y abajo (pilar de portal alto)"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.45, 0
  Poly Array(0, 0, 15, 0, 15, 450, 0, 450)
  CloseSketch "Croquis_perfil", True
  Revolve "Poste_alto_D30x450"
  MountHoles Array(0), 8, 14
  SavePart "T03_Poste_alto_D30x450", "Poste alto esbelto D30 x 450"
  CloseDoc

  NewPart
  OpenSketch GetPlane(1): Rect 0, 0, 275, 25: CloseSketch "Croquis_base", True
  Extrude "Tabique_largo", 300, False
  MountHoles Array(-100, 0, 100), 8, 14
  SavePart "T04_Tabique_largo_275x25x300", "Tabique largo 275x25x300"
  CloseDoc

  NewPart
  OpenSketch GetPlane(0)
  skm.CreateCenterLine 0, 0, 0, 0, 0.3, 0
  Poly Array(0, 0, 30, 0, 30, 300, 0, 300)
  CloseSketch "Croquis_perfil", True
  Revolve "Cilindro_alto_D60x300"
  MountHoles Array(0), 8, 14
  SavePart "T05_Cilindro_alto_D60x300", "Cilindro alto D60 x 300"
  CloseDoc
End Sub

' =====================================================================
'  ENSAMBLAJE DE LA MESA
' =====================================================================
Sub AddComp(asm, fname, x, y, z, cy)
  ' AddComponent4 ubica el CENTRO de la caja envolvente del componente en (x, y+cy, z);
  ' cy = altura del centro de la caja respecto al origen de la pieza.
  On Error Resume Next
  Dim c
  Set c = asm.AddComponent4(outDir & "\" & fname & ".SLDPRT", "", x * MM, (y + cy) * MM, z * MM)
  If c Is Nothing Then WLog "   FALLO componente " & fname
End Sub

Sub BuildAssembly()
  On Error Resume Next
  Dim names, i, asm, r, sx, sz, d
  names = Array("MESA_01_Tablero", "MESA_02_Pata", "MESA_03_Faldon_largo", "MESA_04_Faldon_corto", "MESA_05_Travesano_largo", "MESA_06_Travesano_corto", "MESA_07_Repisa")
  For i = 0 To UBound(names)
    Set d = swApp.OpenDoc(outDir & "\" & names(i) & ".SLDPRT", 1)
  Next
  Set asm = swApp.NewDocument(swApp.GetUserPreferenceStringValue(9), 0, 0, 0)
  AddComp asm, "MESA_01_Tablero", 0, 0, 0, -12.5
  For Each sx In Array(-1, 1)
    For Each sz In Array(-1, 1)
      AddComp asm, "MESA_02_Pata", sx * 565, -750, sz * 465, 362.5
    Next
    AddComp asm, "MESA_03_Faldon_largo", 0, -105, sx * 477.5, 40
    AddComp asm, "MESA_04_Faldon_corto", sx * 477.5, -105, 0, 40
    AddComp asm, "MESA_05_Travesano_largo", 0, -640, sx * 477.5, 20
    AddComp asm, "MESA_06_Travesano_corto", sx * 477.5, -640, 0, 20
  Next
  AddComp asm, "MESA_07_Repisa", 0, -600, 0, 9
  asm.ForceRebuild3 False
  asm.ShowNamedView2 "*Isometric", 7
  asm.ViewZoomtofit2
  r = asm.SaveAs3(outDir & "\MESA_00_Ensamblaje.SLDASM", 0, 1)
  WLog "MESA_00_Ensamblaje  guardado=" & (r = 0) & "  componentes=" & asm.GetComponentCount(True)
  swApp.CloseAllDocuments True
End Sub

Sub BuildAll(dirPath)
  On Error Resume Next
  Dim fso
  outDir = dirPath
  Set fso = CreateObject("Scripting.FileSystemObject")
  If Not fso.FolderExists(outDir) Then fso.CreateFolder outDir
  If Not fso.FolderExists(outDir & "\STEP") Then fso.CreateFolder outDir & "\STEP"
  Set lg = fso.CreateTextFile(outDir & "\registro_generacion.txt", True)
  nOk = 0: nFail = 0
  WLog "SOLIDWORKS " & swApp.RevisionNumber & "  -  " & Now
  swApp.Visible = True
  BuildTable
  BuildObstacles
  BuildAssembly
  WLog "Operaciones OK: " & nOk & "   Fallos: " & nFail
  WLog "FIN"
  lg.Close
End Sub

' ---- arranque (VBScript) ----
Dim argDir
If WScript.Arguments.Count > 0 Then
  argDir = WScript.Arguments(0)
Else
  argDir = CreateObject("WScript.Shell").SpecialFolders("MyDocuments") & "\Mesa_E6_SolidWorks"
End If
Set swApp = CreateObject("SldWorks.Application")
BuildAll argDir
WScript.Echo "Listo. Revise " & argDir & "\registro_generacion.txt"
