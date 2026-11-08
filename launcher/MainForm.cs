namespace GiganSkinLauncher;

/// <summary>Two views: the Monsters home screen (one card per monster) and a monster's skins (one card per skin).
/// The MONSTERS link in the top bar always returns home.</summary>
public sealed class MainForm : Form
{
    static readonly Color Bg = Color.FromArgb(14, 14, 18);
    static readonly Color Red = Color.FromArgb(225, 38, 38);
    const string Note = "Note: Skins are for offline-only use. Use online at your own risk or make sure to switch back to the original look before playing online.";

    // GIGAN_LAUNCHER_NO_AUTODETECT=1 skips the Steam lookup, to try the "browse for game folder" path
    GameInstall? _game = Environment.GetEnvironmentVariable("GIGAN_LAUNCHER_NO_AUTODETECT") == "1" ? null : GameInstall.Find();
    readonly List<Monster> _monsters = Monster.Load(Path.Combine(AppContext.BaseDirectory, "skins"));
    readonly TableLayoutPanel _strip = new() { Dock = DockStyle.Fill, RowCount = 1, Margin = Padding.Empty, Padding = Padding.Empty, BackColor = Bg };
    readonly List<SkinCard> _cards = [];
    readonly Label _home = new() { Text = "MONSTERS", AutoSize = true, Font = new Font("Segoe UI Black", 22f), Cursor = Cursors.Hand };
    readonly Label _crumb = new() { AutoSize = true, Font = new Font("Segoe UI Black", 22f), ForeColor = Red };
    readonly Label _status = new() { AutoSize = false, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, ForeColor = Color.Silver, Text = Note };
    readonly Button _apply = new() { Text = "Apply", Width = 120, Height = 40 };
    readonly Button _launch = new() { Text = "Apply && Play", Width = 150, Height = 40 };
    readonly Button _browse = new() { Text = "Browse for game folder", Width = 210, Height = 40, Visible = false };
    Monster? _monster;
    Skin? _selected;

    public MainForm()
    {
        Text = "Gigan Skin Launcher";
        Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        ClientSize = new Size(860, 560);
        MinimumSize = new Size(640, 440);
        BackColor = Bg;
        ForeColor = Color.White;
        Font = new Font("Segoe UI", 10f);
        StartPosition = FormStartPosition.CenterScreen;

        // top bar: MONSTERS / <monster>, tagline on the right
        var header = new Panel { Dock = DockStyle.Top, Height = 78, BackColor = Bg };
        var sub = new Label { Text = "Gigan is daddy", AutoSize = true, ForeColor = Color.Silver, Font = new Font("Segoe UI", 11f) };
        _home.Location = new Point(22, 16);
        header.Controls.AddRange([_home, _crumb, sub]);
        header.Layout += (_, _) =>
        {
            _crumb.Location = new Point(_home.Right + 2, _home.Top);
            sub.Location = new Point(header.Width - sub.Width - 26, _home.Top + (_home.Height - sub.Height) / 2);
        };
        _home.Click += (_, _) => ShowHome();
        _home.MouseEnter += (_, _) => { if (_monster is not null) _home.ForeColor = Color.White; };
        _home.MouseLeave += (_, _) => _home.ForeColor = _monster is null ? Red : Color.Gray;

        // bottom bar: note + buttons
        var bottom = new TableLayoutPanel { Dock = DockStyle.Bottom, Height = 72, ColumnCount = 4, Padding = new Padding(24, 14, 24, 14), BackColor = Bg };
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        for (var i = 0; i < 3; i++) bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        bottom.Controls.Add(_status, 0, 0);
        bottom.Controls.Add(_browse, 1, 0);
        bottom.Controls.Add(_apply, 2, 0);
        bottom.Controls.Add(_launch, 3, 0);
        foreach (var b in new[] { _browse, _apply, _launch })
        {
            b.FlatStyle = FlatStyle.Flat;
            b.Font = new Font("Segoe UI Semibold", 10.5f);
            b.Cursor = Cursors.Hand;
            b.Margin = new Padding(10, 0, 0, 0);
            b.BackColor = Color.FromArgb(40, 40, 48);
            b.FlatAppearance.BorderColor = Color.FromArgb(80, 80, 92);
        }
        _launch.BackColor = Red;
        _launch.FlatAppearance.BorderColor = Red;
        // flat buttons keep their colour when disabled; grey the red one out so it doesn't look clickable
        _launch.EnabledChanged += (_, _) =>
        {
            _launch.BackColor = _launch.Enabled ? Red : Color.FromArgb(40, 40, 48);
            _launch.FlatAppearance.BorderColor = _launch.Enabled ? Red : Color.FromArgb(80, 80, 92);
        };

        Controls.Add(_strip);
        Controls.Add(header);
        Controls.Add(bottom);

        _apply.Click += (_, _) => ApplySelected(launch: false);
        _launch.Click += (_, _) => ApplySelected(launch: true);
        _browse.Click += (_, _) => BrowseForGame();

        if (_game is null)
        {
            _browse.Visible = true;
            _status.Text = "Game not found automatically. Click Browse and pick the game's folder.";
        }
        ShowHome();
    }

    string ActiveId(Monster m) => _game?.ActiveSkinId(m.Manifest) ?? "";

    void Fill(IEnumerable<(Skin card, string? tag, Action click, Action? doubleClick)> items)
    {
        _strip.SuspendLayout();
        foreach (var c in _cards) c.Dispose();
        _cards.Clear();
        _strip.Controls.Clear();
        _strip.ColumnStyles.Clear();
        var list = items.ToList();
        _strip.ColumnCount = Math.Max(1, list.Count);
        _strip.RowStyles.Clear();
        _strip.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        for (var i = 0; i < list.Count; i++)
        {
            var (skin, tag, click, dbl) = list[i];
            _strip.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f / list.Count));
            var card = new SkinCard(skin) { Dock = DockStyle.Fill, Badge = tag };
            card.Click += (_, _) => click();
            if (dbl is not null) card.DoubleClick += (_, _) => dbl();
            _cards.Add(card);
            _strip.Controls.Add(card, i, 0);
        }
        _strip.ResumeLayout();
    }

    void ShowHome()
    {
        _monster = null;
        _selected = null;
        _home.ForeColor = Red;
        _crumb.Text = "";
        _apply.Visible = _launch.Visible = false;
        Fill(_monsters.Select(m =>
        {
            var active = m.Skins.FirstOrDefault(s => s.Id == ActiveId(m));
            string? tag = active is not null && active.Id != Skin.OriginalId ? $"IN GAME: {active.Name.ToUpperInvariant()}" : null;
            return (m.AsCard, tag, (Action)(() => ShowMonster(m)), (Action?)null);
        }));
        foreach (var c in _cards) c.Selected = true;  // home cards all lit
    }

    void ShowMonster(Monster m)
    {
        _monster = m;
        _home.ForeColor = Color.Gray;
        _crumb.Text = "/ " + m.Name.ToUpperInvariant();
        _apply.Visible = _launch.Visible = true;
        var active = ActiveId(m);
        Fill(m.Skins.Select(s =>
        {
            string? tag = !s.Ready ? "COMING SOON" : s.Id == active ? "IN GAME NOW" : null;
            return (s, tag, (Action)(() => Select(s)), (Action?)(() => { Select(s); ApplySelected(launch: true); }));
        }));
        Select(m.Skins.FirstOrDefault(s => s.Id == active) ?? m.Skins[0]);
    }

    void BrowseForGame()
    {
        using var dlg = new FolderBrowserDialog
        {
            Description = "Pick the Godzilla DAMM Remastered folder (the one that contains GZPro)",
            UseDescriptionForTitle = true,
        };
        if (dlg.ShowDialog(this) != DialogResult.OK) return;
        var found = GameInstall.FromFolder(dlg.SelectedPath);
        if (found is null)
        {
            MessageBox.Show(this, "That doesn't look like the game folder. Pick the folder that contains GZPro.",
                "Game not found", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        found.Remember();
        _game = found;
        _browse.Visible = false;
        _status.Text = Note;
        if (_monster is null) ShowHome(); else ShowMonster(_monster);
    }

    void Select(Skin skin)
    {
        _selected = skin;
        foreach (var c in _cards)
            c.Selected = c.Skin.Id == skin.Id;
        _apply.Enabled = _launch.Enabled = _game is not null && skin.Ready;
    }

    [System.Runtime.InteropServices.DllImport("dwmapi.dll")]
    static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        var dark = 1;
        DwmSetWindowAttribute(Handle, 20, ref dark, sizeof(int));  // DWMWA_USE_IMMERSIVE_DARK_MODE
    }

    void ApplySelected(bool launch)
    {
        if (_game is null || _monster is null || _selected is null || !_selected.Ready) return;
        try
        {
            _game.Apply(_selected, _monster.Manifest);
            var keep = _selected.Id;
            ShowMonster(_monster);
            Select(_monster.Skins.First(s => s.Id == keep));
            if (launch)
            {
                if (!_game.Launch())
                {
                    MessageBox.Show(this, "Skin applied. Start the game the way you normally do.", "Gigan Skin Launcher",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return;
                }
                Close();
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Couldn't switch skins", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }
}
