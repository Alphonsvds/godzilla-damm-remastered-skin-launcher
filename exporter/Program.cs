// Small headless exporter for Godzilla DAMM Remastered (UE 5.8) assets.
//   gzexport list <regex>
//   gzexport json <packagePath> <outFile>
//   gzexport bones <objectPath> <outFile>
//   gzexport export <outDir> <gltf|psk> <packagePath>...
using System.Text.RegularExpressions;
using CUE4Parse.Compression;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Options;
using CUE4Parse_Conversion.Animations;
using CUE4Parse_Conversion.Meshes;
using CUE4Parse.UE4.Objects.Core.Math;
using Newtonsoft.Json;
using Serilog;

var Paks = Environment.GetEnvironmentVariable("GZ_PAKS")
    ?? @"C:\Program Files (x86)\Steam\steamapps\common\Godzilla Destroy All Monsters Melee Remastered\GZPro\Content\Paks";
var usmap = Environment.GetEnvironmentVariable("GZ_USMAP")
    ?? @"C:\Users\halst\OneDrive\Desktop\Projects\gigan-fw-mod\mappings\GZPro.usmap";

Log.Logger = new LoggerConfiguration().MinimumLevel.Warning().WriteTo.Console().CreateLogger();
OodleHelper.Initialize();

var provider = new DefaultFileProvider(Paks, SearchOption.TopDirectoryOnly, new VersionContainer(EGame.GAME_UE5_8));
provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap);
provider.Initialize();
provider.Mount();
Console.Error.WriteLine($"[gz] mounted {provider.Files.Count} files");

switch (args[0])
{
    case "list":
    {
        var rx = new Regex(args[1], RegexOptions.IgnoreCase);
        foreach (var f in provider.Files.Keys.Where(k => rx.IsMatch(k)).Order())
            Console.WriteLine(f);
        break;
    }
    case "json":
    {
        var exports = provider.LoadPackage(args[1]).GetExports();
        File.WriteAllText(args[2], JsonConvert.SerializeObject(exports, Formatting.Indented));
        Console.WriteLine($"wrote {args[2]}");
        break;
    }
    case "bones":
    {
        var obj = provider.LoadPackageObject(args[1]);
        var refSkel = obj switch
        {
            USkeleton s => s.ReferenceSkeleton,
            USkeletalMesh m => m.ReferenceSkeleton,
            _ => throw new Exception($"{obj.ExportType} has no reference skeleton")
        };
        var bones = refSkel.FinalRefBoneInfo.Select((b, i) => new
        {
            name = b.Name.Text,
            parent = b.ParentIndex,
            t = new[] { refSkel.FinalRefBonePose[i].Translation.X, refSkel.FinalRefBonePose[i].Translation.Y, refSkel.FinalRefBonePose[i].Translation.Z },
            q = new[] { refSkel.FinalRefBonePose[i].Rotation.X, refSkel.FinalRefBonePose[i].Rotation.Y, refSkel.FinalRefBonePose[i].Rotation.Z, refSkel.FinalRefBonePose[i].Rotation.W },
            s = new[] { refSkel.FinalRefBonePose[i].Scale3D.X, refSkel.FinalRefBonePose[i].Scale3D.Y, refSkel.FinalRefBonePose[i].Scale3D.Z },
        });
        File.WriteAllText(args[2], JsonConvert.SerializeObject(new { type = obj.ExportType, bones }, Formatting.Indented));
        Console.WriteLine($"wrote {args[2]} ({refSkel.FinalRefBoneInfo.Length} bones)");
        break;
    }
    case "meshinfo":
    {
        // Raw LOD0 vertex bounds and component-space joint positions, in UE units.
        var mesh = provider.LoadPackageObject<USkeletalMesh>(args[1]);
        Console.WriteLine($"ImportedBounds origin={mesh.ImportedBounds.Origin} extent={mesh.ImportedBounds.BoxExtent}");
        if (mesh.TryConvert(out var dto))
        {
            var v = dto.LODs[0].Vertices;
            var lo = v.Aggregate(new FVector(float.MaxValue), (a, x) => new FVector(Math.Min(a.X, x.Position.X), Math.Min(a.Y, x.Position.Y), Math.Min(a.Z, x.Position.Z)));
            var hi = v.Aggregate(new FVector(float.MinValue), (a, x) => new FVector(Math.Max(a.X, x.Position.X), Math.Max(a.Y, x.Position.Y), Math.Max(a.Z, x.Position.Z)));
            Console.WriteLine($"LOD0 {v.Length} verts, {dto.LODs.Count} LODs, bounds min={lo} max={hi}");
            foreach (var s in dto.LODs[0].Sections)
                Console.WriteLine($"  section mat={s.MaterialIndex} first={s.FirstIndex} tris={s.NumFaces}");
        }
        var rs = mesh.ReferenceSkeleton;
        var comp = new FTransform[rs.FinalRefBonePose.Length];
        for (var i = 0; i < comp.Length; i++)
        {
            var p = rs.FinalRefBoneInfo[i].ParentIndex;
            comp[i] = p < 0 ? rs.FinalRefBonePose[i] : rs.FinalRefBonePose[i] * comp[p];
            if (i < 8 || rs.FinalRefBoneInfo[i].Name.Text.EndsWith("Head"))
                Console.WriteLine($"  bone {rs.FinalRefBoneInfo[i].Name.Text,-16} comp pos={comp[i].Translation} scale={comp[i].Scale3D}");
        }
        foreach (var m in mesh.SkeletalMaterials)
            Console.WriteLine($"  slot {m.MaterialSlotName.Text} -> {m.MaterialInterface?.ResolvedObject?.GetPathName()} overlay={m.OverlayMaterialInterface?.ResolvedObject?.GetPathName()}");
        break;
    }
    case "anim":
    {
        // Sample every frame of an animation into per-bone local transforms (skeleton bone order).
        var anim = provider.LoadPackageObject<UAnimSequence>(args[1]);
        var set = anim.ConvertAnims();
        var seq = set.Sequences[0];
        var refPose = set.Skeleton.ReferenceSkeleton.FinalRefBonePose;
        var frames = new List<object>();
        for (var f = 0; f < seq.NumFrames; f++)
        {
            var bones = new List<object>();
            for (var i = 0; i < refPose.Length; i++)
            {
                var q = refPose[i].Rotation; var t = refPose[i].Translation; var s = refPose[i].Scale3D;
                if (i < seq.Tracks.Count) seq.Tracks[i].GetBoneTransform(f, seq.NumFrames, ref q, ref t, ref s);
                bones.Add(new { q = new[] { q.X, q.Y, q.Z, q.W }, t = new[] { t.X, t.Y, t.Z }, s = new[] { s.X, s.Y, s.Z } });
            }
            frames.Add(bones);
        }
        var names = set.Skeleton.ReferenceSkeleton.FinalRefBoneInfo.Select(b => b.Name.Text);
        File.WriteAllText(args[2], JsonConvert.SerializeObject(new { name = seq.Name, fps = seq.FramesPerSecond, bones = names, frames }));
        Console.WriteLine($"wrote {args[2]} ({seq.NumFrames} frames @ {seq.FramesPerSecond} fps, {seq.Tracks.Count} tracks)");
        break;
    }
    case "export":
    {
        var fmt = args[2] == "psk" ? EMeshFormat.ActorX : EMeshFormat.Gltf2;
        var session = new ExportSession();
        foreach (var path in args.Skip(3))
            foreach (var e in provider.LoadPackage(path).GetExports())
            {
                try { session.Add(e); }
                catch (NotSupportedException) { Console.Error.WriteLine($"[gz] skip {e.ExportType} {e.Name}"); }
            }
        var results = await session.RunAsync(args[1], new ExportOptions(meshFormat: fmt, textureFormat: ETextureFormat.Png));
        foreach (var r in results)
            Console.WriteLine($"{(r.Success ? "OK  " : "FAIL")} {r.ObjectPath} {(r.DiskFilePaths is null ? r.Error?.Message : string.Join(", ", r.DiskFilePaths))}");
        break;
    }
}
