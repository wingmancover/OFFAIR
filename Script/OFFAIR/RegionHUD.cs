using UnrealSharp.Attributes;
using UnrealSharp.CoreUObject;
using UnrealSharp.Engine;

namespace Offair.Managed;

/// <summary>Small step-2 HUD; debug content appears only behind F1. Final art/dialogue is step 5.</summary>
[UClass]
public partial class ARegionHUD : AHUD
{
    private ARegionLoopDirector? director;
    public override void ReceiveDrawHUD(int sizeX, int sizeY)
    {
        if (director is null || !SystemLibrary.IsValid(director))
        {
            UGameplayStatics.GetAllActorsOfClass<ARegionLoopDirector>(out var found);
            director = found.FirstOrDefault();
        }
        if (director is null) return;
        var d = director;
        float scale = Math.Clamp(sizeX / 1600f, .65f, 1.7f);
        void Text(string s, float x, float y, FLinearColor color, float font = 1)
            => DrawText(s, color, x, y, null, 2 * scale * font);
        var white = new FLinearColor(.96f,.98f,1,1);
        var cyan = new FLinearColor(.3f,.86f,1,1);
        var dark = new FLinearColor(.007f,.016f,.025f,.94f);
        void Panel(string s, float y, FLinearColor color)
        {
            GetTextSize(s, out var w, out _, null, 2 * scale);
            float x = (sizeX-w)/2;
            DrawRect(dark, x-16*scale,y-10*scale,w+32*scale,44*scale);
            Text(s,x,y,color);
        }
        DrawRect(white,sizeX/2f-3,sizeY/2f-1,6,2);
        DrawRect(dark,20*scale,20*scale,Math.Min(sizeX-40*scale,650*scale),62*scale);
        Text(d.CheckpointSaved ? "MEMORY B / SESSION SAVED" : d.MemoryExperienced ? "A-B REGION / EXPLORE" : "FIND THE RED NOTE",32*scale,28*scale,white);
        Text("WASD Move   SPACE Jump   E Interact   R Loop   F1 GM",32*scale,55*scale,cyan,.72f);
        if (!string.IsNullOrEmpty(d.PromptText)) Panel(d.PromptText,sizeY*.70f,white);
        if (!string.IsNullOrEmpty(d.ThoughtText)) Panel(d.ThoughtText,sizeY-100*scale,cyan);
        if (d.RemoteActive) Panel("GM CAMERA PREVIEW / E or Q to return",100*scale,cyan);
        if (d.GMOpen)
        {
            DrawRect(dark,20*scale,110*scale,690*scale,250*scale);
            string[] rows = {
                "GM / STEP 2 TEST TOOLS - F1 CLOSE",
                $"Attempt {d.AttemptId}   Deaths {d.DeathCount}   HP {d.Health:0}   B {d.CheckpointSaved}",
                $"Gun {d.HasGun}   Card {d.HasAccessCard}   Camera {d.CameraLearned}   Puzzle {d.PuzzleSolved}",
                "1  Die / retry     2  TEST ONLY: grant B prerequisites",
                "3  Teleport near B (does not save)",
                "4  TEST: hide gun / change puzzle state before B",
                "5  TEST: preview C2 camera (no puzzle interaction)"
            };
            for (int i=0;i<rows.Length;i++) Text(rows[i],32*scale,(124+i*32)*scale,white,.85f);
        }
        if (d.Transition != 0)
        {
            DrawRect(new FLinearColor(.005f,.008f,.015f,.90f),0,0,sizeX,sizeY);
            Panel(d.Transition == 1 ? "MEMORY OVERLOAD" : "OFF AIR / REWINDING",sizeY*.45f,white);
            Panel(d.Transition == 1 ? "The memory is tearing through me..." : "Returning to the last memory anchor...",sizeY*.53f,cyan);
        }
        if (!string.IsNullOrEmpty(d.FailureText)) Panel(d.FailureText,sizeY*.25f,new FLinearColor(1,.25f,.2f,1));
    }
}
