using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace GiganSkinLauncher;

/// <summary>A selectable skin: a folder under skins\ holding skin.json, preview.png and the mod's pak/utoc/ucas files.
/// The built-in "Showa" skin is the game's own Gigan: no folder, installs nothing; its card art is skins\original.png.</summary>
public sealed record Skin(string Id, string Name, string Description, string? Folder, string? Preview)
{
    public static readonly Skin Original = new("original", "Showa", "The game's own Gigan, untouched.", null, null);

    public IEnumerable<string> ModFiles => Folder is null
        ? []
        : Directory.EnumerateFiles(Folder).Where(f => Path.GetExtension(f).ToLowerInvariant() is ".pak" or ".utoc" or ".ucas");

    public static List<Skin> Load(string skinsDir)
    {
        var originalArt = Path.Combine(skinsDir, "original.png");
        var skins = new List<Skin> { Original with { Preview = File.Exists(originalArt) ? originalArt : null } };
        if (!Directory.Exists(skinsDir)) return skins;
        foreach (var dir in Directory.EnumerateDirectories(skinsDir).Order())
        {
            var json = Path.Combine(dir, "skin.json");
            if (!File.Exists(json)) continue;
            var doc = JsonDocument.Parse(File.ReadAllText(json)).RootElement;
            string Get(string key, string fallback) => doc.TryGetProperty(key, out var v) ? v.GetString() ?? fallback : fallback;
            var preview = Path.Combine(dir, "preview.png");
            skins.Add(new Skin(Path.GetFileName(dir), Get("name", Path.GetFileName(dir)), Get("description", ""),
                dir, File.Exists(preview) ? preview : null));
        }
        return skins;
    }
}

/// <summary>Finds the game and swaps skin files in and out of its Paks\~mods folder.
/// Only files this launcher installed (listed in its manifest) are ever removed.</summary>
public sealed class GameInstall
{
    public const string SteamAppId = "4251460";
    const string GameFolder = "Godzilla Destroy All Monsters Melee Remastered";
    const string ManifestName = ".gigan-skin-launcher.json";

    public string Root { get; }
    /// <summary>True when found through Steam (launch via Steam); false when the user picked the folder.</summary>
    public bool ViaSteam { get; }
    public string ModsDir => Path.Combine(Root, "GZPro", "Content", "Paks", "~mods");
    string ManifestPath => Path.Combine(ModsDir, ManifestName);

    // a folder the user picked is remembered here so they only browse once
    static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Gigan Skin Launcher", "game-folder.txt");

    GameInstall(string root, bool viaSteam) { Root = root; ViaSteam = viaSteam; }

    public static GameInstall? Find()
    {
        foreach (var lib in SteamLibraries())
        {
            var dir = Path.Combine(lib, "steamapps", "common", GameFolder);
            if (File.Exists(Path.Combine(dir, "GZPro", "Binaries", "Win64", "GZProSteam-Win64-Shipping.exe")))
                return new GameInstall(dir, viaSteam: true);
        }
        try
        {
            if (File.Exists(SettingsPath) && FromFolder(File.ReadAllText(SettingsPath).Trim()) is { } saved)
                return saved;
        }
        catch (IOException) { }
        return null;
    }

    /// <summary>The game install containing <paramref name="picked"/>: accepts the game's main folder or any folder
    /// inside it (GZPro, Content, Paks...). Recognised by GZPro\Content\Paks holding the game's .utoc files.</summary>
    public static GameInstall? FromFolder(string picked)
    {
        for (var dir = new DirectoryInfo(picked); dir is not null; dir = dir.Parent)
        {
            var paks = Path.Combine(dir.FullName, "GZPro", "Content", "Paks");
            if (Directory.Exists(paks) && Directory.EnumerateFiles(paks, "GZPro-*.utoc").Any())
                return new GameInstall(dir.FullName, viaSteam: false);
        }
        return null;
    }

    public void Remember()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath)!);
        File.WriteAllText(SettingsPath, Root);
    }

    static IEnumerable<string> SteamLibraries()
    {
        var steam = Microsoft.Win32.Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null) as string
                    ?? @"C:\Program Files (x86)\Steam";
        steam = steam.Replace('/', '\\');
        yield return steam;
        var vdf = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
        if (!File.Exists(vdf)) yield break;
        foreach (Match m in Regex.Matches(File.ReadAllText(vdf), "\"path\"\\s+\"([^\"]+)\""))
            yield return m.Groups[1].Value.Replace(@"\\", @"\");
    }

    public static bool IsGameRunning() =>
        Process.GetProcesses().Any(p => p.ProcessName.StartsWith("GZPro", StringComparison.OrdinalIgnoreCase) &&
                                        p.ProcessName.Contains("Shipping", StringComparison.OrdinalIgnoreCase));

    public string ActiveSkinId()
    {
        if (!File.Exists(ManifestPath)) return Skin.Original.Id;
        var doc = JsonDocument.Parse(File.ReadAllText(ManifestPath)).RootElement;
        var files = doc.GetProperty("files").EnumerateArray().Select(f => f.GetString()!);
        return files.All(f => File.Exists(Path.Combine(ModsDir, f))) ? doc.GetProperty("skin").GetString()! : Skin.Original.Id;
    }

    public void Apply(Skin skin)
    {
        if (IsGameRunning()) throw new InvalidOperationException("Close the game before switching skins.");
        Directory.CreateDirectory(ModsDir);
        if (File.Exists(ManifestPath))
        {
            var doc = JsonDocument.Parse(File.ReadAllText(ManifestPath)).RootElement;
            foreach (var f in doc.GetProperty("files").EnumerateArray())
            {
                var path = Path.Combine(ModsDir, f.GetString()!);
                if (File.Exists(path)) File.Delete(path);
            }
            File.Delete(ManifestPath);
        }
        var installed = new List<string>();
        foreach (var src in skin.ModFiles)
        {
            var name = Path.GetFileName(src);
            File.Copy(src, Path.Combine(ModsDir, name), overwrite: true);
            installed.Add(name);
        }
        if (installed.Count > 0)
            File.WriteAllText(ManifestPath, JsonSerializer.Serialize(new { skin = skin.Id, files = installed }));
    }

    /// <summary>Starts the game: through Steam when found there, otherwise the game's own executable.
    /// Returns false if no executable could be found (the skin is still applied).</summary>
    public bool Launch()
    {
        if (ViaSteam)
        {
            Process.Start(new ProcessStartInfo($"steam://rungameid/{SteamAppId}") { UseShellExecute = true });
            return true;
        }
        var bin = Path.Combine(Root, "GZPro", "Binaries", "Win64");
        var exe = Directory.Exists(bin) ? Directory.EnumerateFiles(bin, "GZPro*-Shipping.exe").FirstOrDefault() : null;
        exe ??= Directory.EnumerateFiles(Root, "*.exe").FirstOrDefault();
        if (exe is null) return false;
        Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true, WorkingDirectory = Path.GetDirectoryName(exe)! });
        return true;
    }
}
