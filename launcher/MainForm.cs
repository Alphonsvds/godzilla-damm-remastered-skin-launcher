namespace GiganSkinLauncher;

public sealed class MainForm : Form
{
    static readonly Color Bg = Color.FromArgb(14, 14, 18);
    static readonly Color Red = Color.FromArgb(225, 38, 38);
    const string Note = "Note: Skins are for offline-only use. Use online at your own risk or make sure to switch back to Showa before playing online.";

    // GIGAN_LAUNCHER_NO_AUTODETECT=1 skips the Steam lookup, to try the "browse for game folder" path
    GameInstall? _game = Environment.GetEnvironmentVariable("GIGAN_LAUNCHER_NO_AUTODETECT") == "1" ? null : GameInstall.Find();
    readonly List<Skin> _skins = Skin.Load(Path.Combine(AppContext.BaseDirectory, "skins"));
    readonly List<SkinCard> _cards = [];
    readonly Label _status = new() { AutoSize = false, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, ForeColor = Color.Silver };
    readonly Button _apply = new() { Text = "Apply", Width = 120, Height = 40 };
    readonly Button _launch = new() { Text = "Apply && Play", Width = 150, Height = 40 };
    readonly Button _browse = new() { Text = "Browse for game folder", Width = 210, Height = 40, Visible = false };
    Skin _selected = Skin.Original;

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

        // header: GIGAN + tagline
        var header = new Panel { Dock = DockStyle.Top, Height = 78, Padding = new Padding(26, 14, 26, 0), BackColor = Bg };
        var title = new Label { Text = "GIGAN", Font = new Font("Segoe UI Black", 26f), AutoSize = true, ForeColor = Red, Location = new Point(22, 10) };
        var sub = new Label { Text = "Gigan is daddy", AutoSize = true, ForeColor = Color.Silver, Font = new Font("Segoe UI", 11f) };
        header.Controls.Add(title);
        header.Controls.Add(sub);
        header.Layout += (_, _) => sub.Location = new Point(title.Right + 10, title.Bottom - sub.Height - 8);

        // cards: one equal column each, edge to edge
        var strip = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 1, ColumnCount = _skins.Count, Margin = Padding.Empty, Padding = Padding.Empty, BackColor = Bg };
        strip.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        var active = _game?.ActiveSkinId() ?? "";  // nothing is "in game" until the game is found
        for (var i = 0; i < _skins.Count; i++)
        {
            strip.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f / _skins.Count));
            var card = new SkinCard(_skins[i]) { Dock = DockStyle.Fill, InGame = _skins[i].Id == active };
            card.Click += (_, _) => Select(card.Skin);
            card.DoubleClick += (_, _) => { Select(card.Skin); ApplySelected(launch: true); };
            _cards.Add(card);
            strip.Controls.Add(card, i, 0);
        }

        // bottom bar: status + buttons
        var bottom = new TableLayoutPanel { Dock = DockStyle.Bottom, Height = 72, ColumnCount = 4, Padding = new Padding(24, 14, 24, 14), BackColor = Bg };
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        bottom.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
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

        Controls.Add(strip);
        Controls.Add(header);
        Controls.Add(bottom);

        _apply.Click += (_, _) => ApplySelected(launch: false);
        _launch.Click += (_, _) => ApplySelected(launch: true);
        _browse.Click += (_, _) => BrowseForGame();

        Select(_skins.FirstOrDefault(s => s.Id == active) ?? Skin.Original);
        if (_game is null)
        {
            _apply.Enabled = _launch.Enabled = false;
            _browse.Visible = true;
            _status.Text = "Game not found automatically. Click Browse and pick the game's folder.";
        }
        else
        {
            ShowActive(active);
        }
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
        var active = _game.ActiveSkinId();
        Select(_skins.FirstOrDefault(s => s.Id == active) ?? Skin.Original);
        ShowActive(active);
    }

    void Select(Skin skin)
    {
        _selected = skin;
        foreach (var c in _cards)
            c.Selected = c.Skin.Id == skin.Id;
        var ready = skin.Folder is null || skin.ModFiles.Any();
        _apply.Enabled = _launch.Enabled = _game is not null && ready;
    }

    void ShowActive(string id)
    {
        foreach (var c in _cards)
        {
            c.InGame = c.Skin.Id == id;
            c.Invalidate();
        }
        _status.Text = Note;
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
        try
        {
            _game!.Apply(_selected);
            ShowActive(_selected.Id);
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
