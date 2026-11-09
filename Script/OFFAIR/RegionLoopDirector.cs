using UnrealSharp;
using UnrealSharp.Attributes;
using UnrealSharp.CoreUObject;
using UnrealSharp.Engine;
using UnrealSharp.InputCore;

namespace Offair.Managed;

/// <summary>Session-local A-B loop. The authored baseline is captured once, never on death.
/// Future combat/puzzle producers must carry AttemptId and register spawned actors.
/// No static UObject state, disk save, level reload, or dependency on legacy stage numbers.</summary>
[UClass]
public partial class ARegionLoopDirector : AActor
{
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor StartA { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor StartB { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor Note { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor CheckpointTerminal { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor ExitGate { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor TestWeapon { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor PuzzleCamera { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial IList<AActor> BaselineActors { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial IList<AActor> NoteParts { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial USoundBase LoopSound { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial USoundBase SaveSound { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool Initialized { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool MemoryExperienced { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool NoteCollected { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool CheckpointSaved { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool HasGun { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool HasAccessCard { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool CameraLearned { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool PuzzleSolved { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int PuzzleMask { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int AttemptId { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int DeathCount { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int Transition { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial float Health { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool GMOpen { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool RemoteActive { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool DebugPrepared { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string PromptText { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string ThoughtText { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string FailureText { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int LoopSoundCount { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int SaveSoundCount { get; set; }

    private sealed record Baseline(AActor Actor, FTransform Transform, bool Hidden, bool Collision);
    private readonly List<Baseline> baseline = new();
    private readonly List<AActor> transients = new();
    private APlayerController? controller;
    private ACharacter? player;
    private float remaining, thoughtRemaining;
    private bool firstMemoryDeath;
    private bool savedGun, savedCard, savedLearned, savedNote, savedDebug;
    private int savedMask;
    private AActor? focused;
    private static bool Alive(AActor? a) => a is not null && SystemLibrary.IsValid(a);

    // Called from the Blueprint tick, keeping editor authoring and runtime responsibilities explicit.
    [UFunction(FunctionFlags.BlueprintCallable)]
    public void StepRegion(float delta)
    {
        if (!Initialized)
        {
            controller = UGameplayStatics.GetPlayerController(0);
            player = UGameplayStatics.GetPlayerCharacter(0);
            if (!Alive(controller) || !Alive(player)) return;
            if (!Alive(StartA) || !Alive(StartB) || !Alive(Note) || !Alive(CheckpointTerminal) || !Alive(ExitGate)
                || BaselineActors.Count == 0 || BaselineActors.Any(a => !Alive(a)))
            {
                FailureText = "REGION SETUP INCOMPLETE - check assigned references.";
                return; // Fail closed; do not capture a partial baseline or lock the player.
            }
            baseline.Clear();
            foreach (var a in BaselineActors.Distinct())
                baseline.Add(new(a, a.ActorTransform, a.ActorHiddenInGame, a.ActorEnableCollision));
            Health = 100; AttemptId = 1; Initialized = true;
            PromptText = ""; ThoughtText = ""; FailureText = "";
        }
        if (!Alive(player) || !Alive(controller)) { FailureText = "Player unavailable. Restart PIE."; return; }
        if (RemoteActive && !Alive(PuzzleCamera)) ExitRemote();
        thoughtRemaining = Math.Max(0, thoughtRemaining - delta);
        if (thoughtRemaining == 0) ThoughtText = "";
        if (Transition != 0)
        {
            remaining -= delta;
            if (remaining <= 0)
            {
                if (Transition == 1) BeginDeath(true);
                else FinishDeath();
            }
        }
        UpdateFocus();
        // Real engine input, independent of desktop focus automation. Never synthesize OS keys.
        foreach (var key in new[] { "F1", "E", "R", "Q", "One", "Two", "Three", "Four", "Five" })
            if (controller!.WasInputKeyJustPressed(new FKey(key))) HandleRegionInput(key);
        if (Transition == 0 && player!.ActorLocation.Z < -300) RequestRegionDeath(AttemptId);
    }

    private bool AimAt(AActor target, float range)
    {
        controller!.GetPlayerViewPoint(out var origin, out var rotation);
        var targetPosition = target.ActorLocation;
        var to = targetPosition - origin;
        if (to.Length() > range) return false;
        var forward = MathLibrary.GetForwardVector(rotation);
        var dot = to.X * forward.X + to.Y * forward.Y + to.Z * forward.Z;
        // Small angular tolerance helps thin floor notes, while tracing for occluders.
        if (dot < to.Length() * .965) return false;
        var hit = SystemLibrary.LineTraceByChannel(origin, targetPosition,
            ETraceTypeQuery.TraceTypeQuery1, false, new List<AActor> { player!, this },
            EDrawDebugTrace.None, out var result, true);
        return !hit || result.Actor == target || (result.ImpactPoint - targetPosition).Length() < 8;
    }

    private void UpdateFocus()
    {
        focused = null; PromptText = "";
        if (!Initialized || Transition != 0 || RemoteActive) return;
        if (!CheckpointSaved && !NoteCollected && Alive(Note) && AimAt(Note, 330))
        { focused = Note; PromptText = "[E] Read the red note"; }
        else if (Alive(CheckpointTerminal) && AimAt(CheckpointTerminal, 360))
        { focused = CheckpointTerminal; PromptText = CheckpointSaved ? "MEMORY B / Saved for this session" : "[E] Recover memory / Checkpoint B"; }
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public void HandleRegionInput(string key)
    {
        if (!Initialized) return;
        if (key == "F1") { GMOpen = !GMOpen; return; }
        if (Transition != 0) return;
        if (key == "Q") { ExitRemote(); return; }
        if (key == "R") { RequestRegionDeath(AttemptId); return; }
        if (key == "E")
        {
            if (RemoteActive) { ExitRemote(); return; }
            UpdateFocus(); // Never trust an old prompt when the player turns away.
            if (focused == Note) ReadNote();
            else if (focused == CheckpointTerminal) TrySaveCheckpoint();
            return;
        }
        if (!GMOpen) return;
        if (key == "One") RequestRegionDeath(AttemptId);
        if (key == "Two") DebugPrepareCheckpoint();
        if (key == "Three")
        {
            ExitRemote();
            player!.SetActorLocation(new FVector(9000, 4400, 100), false, out _, true);
            controller!.ControlRotation = MathLibrary.FindLookAtRotation(new FVector(9000,4400,170), CheckpointTerminal.ActorLocation);
        }
        if (key == "Four")
        {
            if (CheckpointSaved) { Say("Completed region is frozen. Restart PIE for another A-B test."); return; }
            if (Alive(TestWeapon)) TestWeapon.ActorHiddenInGame = true;
            PuzzleMask = 21;
            Say("GM TEST: weapon hidden; puzzle state changed. R should restore both.");
        }
        if (key == "Five" && Alive(PuzzleCamera))
        {
            if (RemoteActive) ExitRemote();
            else { RemoteActive = true; LockInput(true); controller!.SetViewTargetWithBlend(PuzzleCamera); }
        }
    }

    private void ReadNote()
    {
        if (NoteCollected || CheckpointSaved || Transition != 0) return;
        NoteCollected = true;
        foreach (var a in NoteParts) if (Alive(a)) { a.ActorHiddenInGame = true; a.ActorEnableCollision = false; }
        if (!MemoryExperienced)
        {
            Transition = 1; remaining = 3; ThoughtText = ""; thoughtRemaining = 0;
            LockInput(true);
        }
        else Say("I remember this. I can leave the note and go straight to the guns.");
    }

    private void LockInput(bool locked)
    {
        if (!Alive(controller) || !Alive(player)) return;
        controller!.ResetIgnoreInputFlags();
        controller.IgnoreMoveInput = locked; controller.IgnoreLookInput = locked;
        if (locked) { player!.StopJumping(); player.CharacterMovement.StopMovementImmediately(); player.DisableInput(controller); }
        else player!.EnableInput(controller);
    }

    private void ExitRemote()
    {
        RemoteActive = false;
        if (Alive(player) && Alive(controller)) controller!.SetViewTargetWithBlend(player!);
        if (Transition == 0) LockInput(false);
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public bool RequestRegionDeath(int expectedAttempt)
    {
        if (!Initialized || Transition != 0 || expectedAttempt != AttemptId || !Alive(player) || !Alive(controller)) return false;
        BeginDeath(false); return true;
    }

    private void BeginDeath(bool memory)
    {
        firstMemoryDeath = memory;
        ExitRemote(); Transition = 2; remaining = .65f; AttemptId++; DeathCount++; Health = 0;
        ThoughtText = ""; thoughtRemaining = 0; focused = null; PromptText = "";
        LockInput(true);
        if (LoopSound is not null) { UGameplayStatics.PlaySound2D(LoopSound, .65f); LoopSoundCount++; }
    }

    private void FinishDeath()
    {
        foreach (var a in transients) if (Alive(a)) a.DestroyActor();
        transients.Clear();
        if (!CheckpointSaved)
        {
            // Actors are retained, not destroyed; this restores all explicitly registered geometry state.
            if (baseline.Any(b => !Alive(b.Actor)))
            { FailureText = "A baseline actor was destroyed. Restart PIE; reset cancelled safely."; remaining = float.PositiveInfinity; return; }
            foreach (var b in baseline)
            {
                b.Actor.SetActorTransform(b.Transform, false, out _, true);
                b.Actor.ActorHiddenInGame = b.Hidden; b.Actor.ActorEnableCollision = b.Collision;
            }
            NoteCollected = false; HasGun = false; HasAccessCard = false; CameraLearned = false;
            PuzzleSolved = false; PuzzleMask = 0; DebugPrepared = false;
        }
        else
        {
            // The completed A-B region is frozen in place. Restore only saved player progression.
            HasGun = savedGun; HasAccessCard = savedCard; CameraLearned = savedLearned;
            NoteCollected = savedNote; PuzzleSolved = true; PuzzleMask = savedMask; DebugPrepared = savedDebug;
        }
        MemoryExperienced |= firstMemoryDeath;
        var spawn = CheckpointSaved ? StartB : StartA;
        player!.SetActorLocationAndRotation(spawn.ActorLocation, spawn.ActorRotation, false, out _, true);
        player.CharacterMovement.StopMovementImmediately();
        controller!.ControlRotation = spawn.ActorRotation;
        controller.SetViewTargetWithBlend(player);
        Transition = 0; Health = 100; LockInput(false);
        Say(CheckpointSaved ? "I'm back at the memory. The completed area is still intact."
            : MemoryExperienced ? "Back again... I remember the note. This time, I can go straight to the guns."
            : "Back at the beginning. That red note is still here.", 5);
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public void ApplyRegionDamage(float damage, int expectedAttempt)
    {
        if (!Initialized || Transition != 0 || expectedAttempt != AttemptId || damage <= 0) return;
        Health = Math.Max(0, Health - damage);
        if (Health == 0) RequestRegionDeath(expectedAttempt);
    }

    // Progress event contract for the later weapon, card, camera and puzzle implementations.
    [UFunction(FunctionFlags.BlueprintCallable)]
    public bool ReportRegionProgress(int expectedAttempt, int kind)
    {
        if (!Initialized || Transition != 0 || CheckpointSaved || expectedAttempt != AttemptId || !MemoryExperienced) return false;
        switch (kind)
        {
            case 0: HasGun = true; return true;
            case 1 when HasGun: HasAccessCard = true; return true;
            case 2 when HasAccessCard: CameraLearned = true; return true;
            case 3 when HasGun && HasAccessCard && CameraLearned:
                PuzzleSolved = true; ExitGate.ActorHiddenInGame = true; ExitGate.ActorEnableCollision = false; return true;
            default: return false;
        }
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public bool RegisterRegionTransient(AActor actor, int expectedAttempt)
    {
        if (!Alive(actor) || actor == this || actor == player || baseline.Any(b => b.Actor == actor)) return false;
        if (expectedAttempt != AttemptId || Transition != 0 || CheckpointSaved) { actor.DestroyActor(); return false; }
        if (!transients.Contains(actor)) transients.Add(actor);
        return true;
    }

    private void DebugPrepareCheckpoint()
    {
        if (!MemoryExperienced) { Say("TEST SETUP requires the first note / memory death first."); return; }
        if (CheckpointSaved) return;
        DebugPrepared = true;
        for (int i = 0; i < 4; i++) ReportRegionProgress(AttemptId, i);
        if (Alive(TestWeapon)) TestWeapon.ActorHiddenInGame = true;
        PuzzleMask = 73;
        Say("GM TEST ONLY: prerequisites granted. Go to B and press E to save.");
    }

    private void TrySaveCheckpoint()
    {
        if (CheckpointSaved || Transition != 0) return;
        if (!(MemoryExperienced && HasGun && HasAccessCard && CameraLearned && PuzzleSolved))
        { Say("Memory locked: weapon, camera access, camera learning and puzzle completion required."); return; }
        ExitRemote();
        savedGun = HasGun; savedCard = HasAccessCard; savedLearned = CameraLearned;
        savedNote = NoteCollected; savedMask = PuzzleMask; savedDebug = DebugPrepared;
        CheckpointSaved = true;
        transients.Clear(); // Remaining A-B actors now belong to the frozen, completed region.
        if (SaveSound is not null) { UGameplayStatics.PlaySound2D(SaveSound, .65f); SaveSoundCount++; }
        Say("MEMORY RECOVERED / Checkpoint B saved for this session.");
    }

    private void Say(string text, float seconds = 5) { ThoughtText = text; thoughtRemaining = seconds; }
}
