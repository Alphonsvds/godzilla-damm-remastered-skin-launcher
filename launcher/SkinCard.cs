using System.ComponentModel;
using System.Diagnostics;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;

namespace GiganSkinLauncher;

public sealed class SkinCard : Control
{
    const float MaxZoom = 1.07f;
    const float DimIdle = 0.70f, DimHover = 0.30f, DimSelected = 0.02f;
    const double DurationMs = 280;
    const float FocusY = 0.42f;

    readonly System.Windows.Forms.Timer _anim = new() { Interval = 10 };
    readonly Stopwatch _clock = Stopwatch.StartNew();
    readonly Image? _art;
    Bitmap? _cache;
    Size _cacheFor;
    float _zoom = 1f, _zoomFrom = 1f, _zoomTo = 1f, _dim = DimIdle, _dimFrom = DimIdle, _dimTo = DimIdle;
    double _startMs;
    bool _selected, _hover;

    public Skin Skin { get; }

    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public string? Badge { get; set; }

    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool Selected
    {
        get => _selected;
        set { _selected = value; Retarget(); }
    }

    public SkinCard(Skin skin)
    {
        Skin = skin;
        if (skin.Preview is not null)
            _art = Image.FromStream(new MemoryStream(File.ReadAllBytes(skin.Preview)));
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint |
                 ControlStyles.ResizeRedraw, true);
        Cursor = Cursors.Hand;
        Margin = Padding.Empty;
        _anim.Tick += (_, _) => Step();
    }

    protected override void OnMouseEnter(EventArgs e) { _hover = true; Retarget(); base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { _hover = false; Retarget(); base.OnMouseLeave(e); }

    void Retarget()
    {
        _zoomFrom = _zoom;
        _dimFrom = _dim;
        _zoomTo = _hover ? MaxZoom : 1f;
        _dimTo = _selected ? DimSelected : _hover ? DimHover : DimIdle;
        _startMs = _clock.Elapsed.TotalMilliseconds;
        _anim.Start();
    }

    void Step()
    {
        var t = Math.Min(1.0, (_clock.Elapsed.TotalMilliseconds - _startMs) / DurationMs);
        var ease = (float)(1 - Math.Pow(1 - t, 3));
        _zoom = _zoomFrom + (_zoomTo - _zoomFrom) * ease;
        _dim = _dimFrom + (_dimTo - _dimFrom) * ease;
        if (t >= 1)
            _anim.Stop();
        Invalidate();
    }

    Bitmap? Cache()
    {
        if (_art is null || Width <= 0 || Height <= 0)
            return null;
        if (_cache is not null && _cacheFor == Size)
            return _cache;
        _cache?.Dispose();
        _cacheFor = Size;
        var cw = (int)Math.Ceiling(Width * MaxZoom);
        var ch = (int)Math.Ceiling(Height * MaxZoom);
        _cache = new Bitmap(cw, ch, PixelFormat.Format32bppPArgb);
        using var g = Graphics.FromImage(_cache);
        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;
        var scale = Math.Max(cw / (float)_art.Width, ch / (float)_art.Height);
        var w = _art.Width * scale;
        var h = _art.Height * scale;
        g.DrawImage(_art, new RectangleF(cw / 2f - w / 2f, ch * FocusY - h * FocusY, w, h));
        return _cache;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        var r = ClientRectangle;
        g.Clear(Color.FromArgb(16, 16, 20));

        var cache = Cache();
        if (cache is not null)
        {
            g.InterpolationMode = InterpolationMode.HighQualityBilinear;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;
            var sw = cache.Width * (1f / _zoom) * (r.Width / (float)cache.Width) * MaxZoom;
            var sh = cache.Height * (1f / _zoom) * (r.Height / (float)cache.Height) * MaxZoom;
            var sx = cache.Width / 2f - sw / 2f;
            var sy = cache.Height * FocusY - sh * FocusY;
            g.DrawImage(cache, r, sx, sy, sw, sh, GraphicsUnit.Pixel);
        }

        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
        using (var dim = new SolidBrush(Color.FromArgb((int)(_dim * 255), 0, 0, 0)))
            g.FillRectangle(dim, r);
        var fadeTop = r.Height * 0.45f;
        using (var fade = new LinearGradientBrush(new PointF(0, fadeTop), new PointF(0, r.Height),
                   Color.FromArgb(0, 0, 0, 0), Color.FromArgb(235, 0, 0, 0)))
            g.FillRectangle(fade, 0, fadeTop, r.Width, r.Height - fadeTop);

        const int pad = 22;
        using var nameFont = new Font("Segoe UI Black", Math.Max(16f, r.Width / 12.5f), FontStyle.Regular, GraphicsUnit.Pixel);
        var nameRect = new RectangleF(pad, 0, r.Width - pad * 2, r.Height - pad - (Badge is null ? 0 : 30));
        using var fmt = new StringFormat { LineAlignment = StringAlignment.Far, Alignment = StringAlignment.Near };
        using (var shadow = new SolidBrush(Color.FromArgb(160, 0, 0, 0)))
            g.DrawString(Skin.Name.ToUpperInvariant(), nameFont, shadow, new RectangleF(nameRect.X + 2, nameRect.Y + 2, nameRect.Width, nameRect.Height), fmt);
        g.DrawString(Skin.Name.ToUpperInvariant(), nameFont, Brushes.White, nameRect, fmt);
        if (Badge is not null)
        {
            using var tagFont = new Font("Segoe UI Semibold", 11f, GraphicsUnit.Pixel);
            var tag = Badge;
            var size = g.MeasureString(tag, tagFont);
            var tagRect = new RectangleF(pad, r.Height - pad - 20, size.Width + 14, 20);
            using var path = Rounded(tagRect, 10);
            using var tagBrush = new SolidBrush(Color.FromArgb(200, 255, 255, 255));
            g.FillPath(tagBrush, path);
            using var tagText = new SolidBrush(Color.FromArgb(20, 20, 24));
            g.DrawString(tag, tagFont, tagText, tagRect.X + 7, tagRect.Y + (20 - size.Height) / 2);
        }
    }

    static GraphicsPath Rounded(RectangleF r, float radius)
    {
        var p = new GraphicsPath();
        var d = radius * 2;
        p.AddArc(r.X, r.Y, d, d, 180, 90);
        p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
        p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
        p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
        p.CloseFigure();
        return p;
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _anim.Dispose();
            _art?.Dispose();
            _cache?.Dispose();
        }
        base.Dispose(disposing);
    }
}
