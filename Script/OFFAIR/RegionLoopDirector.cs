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
    [UProperty(PropertyFlags.EditAnywhere)] public partial float MaximumHealth { get; set; }
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
    private readonly List<(USkeletalMeshComponent Mesh, TSubclassOf<UObject> AnimClass)> unarmedPose = new();
    private readonly List<AActor> retiringProjectiles = new();
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
        // Damage may request a reset inside a projectile's own Hit callback. Let that stack
        // finish before destroying its components or any other in-flight projectile.
        foreach (var a in retiringProjectiles) if (Alive(a)) a.DestroyActor();
        retiringProjectiles.Clear();
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
            Health = MaximumHealth > 0 ? MaximumHealth : 500; AttemptId = 1; Initialized = true;
            PromptText = ""; ThoughtText = ""; FailureText = "";
            InitializeTutorial();
            if (Initialized) InitializePuzzle();
        }
        if (!Alive(player) || !Alive(controller)) { FailureText = "Player unavailable. Restart PIE."; return; }
        if (RemoteActive && !Alive(remoteTarget)) ExitRemote(false);
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
        TickTutorial(delta);
        TickPuzzle(delta);
        TickVista(delta);
        TickNarrative(delta);
        // Real engine input, independent of desktop focus automation. Never synthesize OS keys.
        foreach (var key in new[] { "F1", "E", "Q", "SpaceBar", "One", "Two", "Three", "Four", "Five", "Six", "Seven" })
            if (controller!.WasInputKeyJustPressed(new FKey(key))) HandleRegionInput(key);
        if (controller!.WasInputKeyJustReleased(new FKey("LeftMouseButton"))) SetRegionFiring(false);
        if (controller.WasInputKeyJustPressed(new FKey("LeftMouseButton"))) SetRegionFiring(true);
        if (Transition == 0 && player!.ActorLocation.Z < -300) RequestRegionDeath(AttemptId);
    }

    private bool AimAt(AActor target, float range, double alignment = .965)
    {
        controller!.GetPlayerViewPoint(out var origin, out var rotation);
        target.GetActorBounds(false, out var targetPosition, out _, false);
        var to = targetPosition - origin;
        if (to.Length() > range) return false;
        var forward = MathLibrary.GetForwardVector(rotation);
        var dot = to.X * forward.X + to.Y * forward.Y + to.Z * forward.Z;
        // Small angular tolerance helps thin floor notes, while tracing for occluders.
        if (dot < to.Length() * alignment) return false;
        var hit = SystemLibrary.LineTraceByChannel(origin, targetPosition,
            ETraceTypeQuery.TraceTypeQuery1, false, new List<AActor> { player!, this },
            EDrawDebugTrace.None, out var result, true);
        return !hit || result.Actor == target || (result.ImpactPoint - targetPosition).Length() < 8;
    }

    private void UpdateFocus()
    {
        focused = null; PromptText = "";
        if (!Initialized || Transition != 0 || RemoteActive || VistaActive) return;
        if (UpdateTutorialFocus()) return;
        if (UpdatePuzzleFocus()) return;
        if (!CheckpointSaved && !NoteCollected && Alive(Note) && AimAt(Note, 330))
        { focused = Note; PromptText = "[E] Read the red note"; }
        else if (Alive(CheckpointTerminal) && AimAt(CheckpointTerminal, 360))
        { focused = CheckpointTerminal; PromptText = CheckpointSaved ? "MEMORY B / Saved for this session" : "[E] Recover memory / Checkpoint B"; }
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public void HandleRegionInput(string key)
    {
        if (!Initialized) return;
        if (key == "F1") { SetRegionFiring(false); GMOpen = !GMOpen; return; }
        if (Transition != 0 || (PuzzleSubmitting && !(GMOpen && key == "One"))) return;
        if (VistaActive)
        {
            if (key == "SpaceBar" || key == "E" || key == "Q") ReturnFromVista(true);
            else if (GMOpen && key == "One") RequestRegionDeath(AttemptId);
            return;
        }
        if (key == "Q") { ExitRemote(); return; }
        if (key == "E")
        {
            if (RemoteActive) { ExitRemote(); return; }
            UpdateFocus(); // Never trust an old prompt when the player turns away.
            if (InteractTutorialFocus()) return;
            if (InteractPuzzleFocus()) return;
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
        HandleTutorialGM(key);
    }

    private void ReadNote()
    {
        if (NoteCollected || CheckpointSaved || Transition != 0) return;
        NoteCollected = true;
        foreach (var a in NoteParts) if (Alive(a)) { a.ActorHiddenInGame = true; a.ActorEnableCollision = false; }
        if (!MemoryExperienced)
        {
            ClearDialogue();
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

    private void ExitRemote(bool normal = true)
    {
        bool wasRemote = RemoteActive;
        CompleteRemoteLesson(normal);
        RemoteActive = false;
        remoteTarget = null;
        if (Alive(player) && Alive(controller)) controller!.SetViewTargetWithBlend(player!);
        if (wasRemote && Alive(controller)) controller!.ControlRotation = bodyRotation;
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
        FinishVista(); ClearDialogue(); NoticeText=""; noticeRemaining=0;
        CancelPuzzleAttempt();
        ExitRemote(false); StopTutorialCombat(); Transition = 2; remaining = .65f; AttemptId++; DeathCount++; Health = 0;
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
            ResetTutorial();
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
            ResetPuzzle();
        }
        else
        {
            // The completed A-B region is frozen in place. Restore only saved player progression.
            HasGun = savedGun; HasAccessCard = savedCard; CameraLearned = savedLearned;
            NoteCollected = savedNote; PuzzleSolved = true; PuzzleMask = savedMask; DebugPrepared = savedDebug;
            RestoreSavedWeapon();
        }
        MemoryExperienced |= firstMemoryDeath;
        var spawn = CheckpointSaved ? StartB : StartA;
        player!.SetActorLocationAndRotation(spawn.ActorLocation, spawn.ActorRotation, false, out _, true);
        player.CharacterMovement.StopMovementImmediately();
        controller!.ControlRotation = spawn.ActorRotation;
        controller.SetViewTargetWithBlend(player);
        Transition = 0; Health = MaximumHealth > 0 ? MaximumHealth : 500; FailureText = ""; LockInput(false);
        Say(CheckpointSaved ? "I'm back at the memory. The completed area is still intact."
            : MemoryExperienced ? RepeatThought()
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
        if (!MemoryExperienced) { Notice("TEST SETUP requires the first note / memory death first."); return; }
        if (CheckpointSaved) return;
        DebugPrepared = true;
        StopTutorialCombat();
        if (!Alive(heldWeapon)) heldWeapon = EquipTutorialWeapon(player!, 2);
        ChosenWeapon = 2;
        for (int i = 0; i < 4; i++) ReportRegionProgress(AttemptId, i);
        if (Alive(TestWeapon)) TestWeapon.ActorHiddenInGame = true;
        SetTutorialGate(true);
        PuzzleMask = 73;
        RefreshPuzzleTiles();
        Notice("GM TEST ONLY: prerequisites granted. Go to B and press E to save.");
    }

    private void TrySaveCheckpoint()
    {
        if (CheckpointSaved || Transition != 0) return;
        if (!(MemoryExperienced && HasGun && HasAccessCard && CameraLearned && PuzzleSolved))
        { Notice("Memory locked: complete the weapon, camera and puzzle objectives."); return; }
        ExitRemote();
        savedGun = HasGun; savedCard = HasAccessCard; savedLearned = CameraLearned;
        savedNote = NoteCollected; savedMask = PuzzleMask; savedDebug = DebugPrepared;
        savedChoice = ChosenWeapon;
        CheckpointSaved = true;
        ClearProjectiles();
        transients.Clear(); // Remaining A-B actors now belong to the frozen, completed region.
        if (SaveSound is not null) { UGameplayStatics.PlaySound2D(SaveSound, .65f); SaveSoundCount++; }
        ClearDialogue();
        Notice("MEMORY B RECOVERED / Progress saved for this session.");
        Say("This memory is mine. I won't lose what I've learned here.");
    }

    private void Say(string text, float seconds = 5, string guard = "")
    {
        ThoughtText=text; thoughtRemaining=seconds; // Last-event diagnostics, not parallel HUD subtitles.
        QueueDialogue(text,2,guard);
    }

    // Teaching room: template adapters, encounters, and camera lesson.

    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor AlternativeWeapon { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor AccessCard { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor TutorialCamera { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor TutorialCameraTarget { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor TutorialGate { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial IList<AActor> GuardSpawnPoints { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial USoundBase CameraEnterSound { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial USoundBase CameraExitSound { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int ChosenWeapon { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int LivingGuards { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int KilledGuards { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool CardDropped { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string HostText { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool LessonTurned { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int Ammo { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool WaveRewardEligible { get; set; }

    // Explicit adapters implemented by BP_RegionLoopDirector, reusing template assets.
    [UFunction(FunctionFlags.BlueprintEvent)] public partial AActor EquipTutorialWeapon(ACharacter holder, int choice);
    public partial AActor EquipTutorialWeapon_Implementation(ACharacter holder, int choice) => null!;
    [UFunction(FunctionFlags.BlueprintEvent)] public partial void ClearTutorialWeapon(ACharacter holder);
    public partial void ClearTutorialWeapon_Implementation(ACharacter holder) { }
    [UFunction(FunctionFlags.BlueprintEvent)] public partial void FireTutorialWeapon(AActor weapon, bool firing);
    public partial void FireTutorialWeapon_Implementation(AActor weapon, bool firing) { }
    [UFunction(FunctionFlags.BlueprintEvent)] public partial AActor SpawnTutorialGuard(FTransform transform);
    public partial AActor SpawnTutorialGuard_Implementation(FTransform transform) => null!;
    [UFunction(FunctionFlags.BlueprintEvent)] public partial float GetTutorialGuardHealth(AActor guard);
    public partial float GetTutorialGuardHealth_Implementation(AActor guard) => 100;
    [UFunction(FunctionFlags.BlueprintEvent)] public partial void RemoveTutorialGuard(AActor guard);
    public partial void RemoveTutorialGuard_Implementation(AActor guard) { }
    [UFunction(FunctionFlags.BlueprintEvent)] public partial int GetTutorialAmmo(AActor weapon);
    public partial int GetTutorialAmmo_Implementation(AActor weapon) => 0;

    private readonly List<AActor> guards = new();
    private readonly Dictionary<AActor, AController> guardControllers = new(ReferenceEqualityComparer.Instance);
    private readonly HashSet<AActor> countedDeaths = new(ReferenceEqualityComparer.Instance);
    private readonly List<AActor> regionProjectiles = new();
    private AActor? heldWeapon, remoteTarget;
    private FRotator bodyRotation, remoteEntryRotation;
    private bool remoteLesson, gunIntroduction;
    // Experienced knowledge survives an A-B retry, unlike the camera access/lesson gates.
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool CameraLessonNarrated { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool CardDiscoveryNarrated { get; set; }
    private int requiredKills, savedChoice, previousChoice;
    private float hostRemaining;

    private void InitializeTutorial()
    {
        HostText = "";
        if (!Alive(AlternativeWeapon) || !Alive(AccessCard) || !Alive(TutorialCamera) || !Alive(TutorialGate)
            || !Alive(TutorialCameraTarget) || GuardSpawnPoints.Count != 10 || GuardSpawnPoints.Any(a => !Alive(a)))
        { Initialized = false; FailureText = "TEACHING ROOM SETUP INCOMPLETE - check assigned references."; return; }
        unarmedPose.Clear();
        foreach (var mesh in player!.GetComponentsByClass<USkeletalMeshComponent>())
            unarmedPose.Add((mesh, mesh.GetAnimClass()));
        Host("Welcome to the arena. Take a look around. Our audience is waiting.");
    }

    private bool UpdateTutorialFocus()
    {
        if (CheckpointSaved) return false;
        if (!HasGun)
        {
            foreach (var a in new[] { TestWeapon, AlternativeWeapon })
            {
                if (!Alive(a) || !AimAt(a, 350, .992)) continue;
                focused = a;
                PromptText = !MemoryExperienced ? "Recover the red note first"
                    : a == TestWeapon ? "[E] Take AMBER pistol / Host's choice" : "[E] Take CYAN pistol";
                return true;
            }
        }
        if (CardDropped && !HasAccessCard && Alive(AccessCard) && AimAt(AccessCard, 350, .99))
        { focused = AccessCard; PromptText = "[E] Pick up camera access card"; return true; }
        if (Alive(TutorialCamera) && Alive(TutorialCameraTarget) && AimAt(TutorialCameraTarget, 2000, .998))
        { focused = TutorialCamera; PromptText = HasAccessCard ? "[E] Hack training camera" : "Camera access card required"; return true; }
        return false;
    }

    private bool InteractTutorialFocus()
    {
        if (focused == TestWeapon || focused == AlternativeWeapon)
        { if (MemoryExperienced) ChooseWeapon(focused == TestWeapon ? 1 : 2); return true; }
        if (focused == AccessCard)
        {
            if (CardDropped && LivingGuards == 0 && WaveRewardEligible && ReportRegionProgress(AttemptId, 1))
            {
                AccessCard.ActorHiddenInGame = true;
                Host("There's your access. Look up at the training camera and take control.");
                if (!CardDiscoveryNarrated)
                {
                    CardDiscoveryNarrated=true;
                    Say("Their cameras... maybe I can see what they see.");
                }
            }
            return true;
        }
        if (focused == TutorialCamera)
        { if (HasAccessCard) EnterTutorialRemote(TutorialCamera, true); return true; }
        return false;
    }

    private void ChooseWeapon(int choice)
    {
        if (!MemoryExperienced || HasGun || Transition != 0 || CheckpointSaved) return;
        heldWeapon = EquipTutorialWeapon(player!, choice);
        if (!Alive(heldWeapon)) { FailureText = "Weapon could not be equipped. F1 / 1 to retry."; return; }
        HasGun = true; ChosenWeapon = choice; WaveRewardEligible = true;
        TestWeapon.ActorHiddenInGame = true; AlternativeWeapon.ActorHiddenInGame = true;
        requiredKills = choice == 1 ? 10 : 2;
        for (int i=0; i<requiredKills; i++)
        {
            var guard = SpawnTutorialGuard(GuardSpawnPoints[i].ActorTransform);
            if (!Alive(guard))
            {
                WaveRewardEligible = false; StopTutorialCombat();
                FailureText = "Encounter could not start completely. F1 / 1 to retry.";
                return;
            }
            TrackGuard(guard);
        }
        LivingGuards = guards.Count;
        Host(choice == 1 ? "Excellent taste. Let's give you a proper welcome!"
            : "The cyan one? Not my recommendation. Make it entertaining, then.");
        if (choice == 2 && previousChoice == 1) Say("A different choice. Let's see if it changes my chances.");
    }

    private void TickTutorial(float delta)
    {
        hostRemaining = Math.Max(0, hostRemaining - delta);
        if (hostRemaining == 0) HostText = "";
        regionProjectiles.RemoveAll(a => !Alive(a));
        if (Transition != 0 || !Initialized) return;
        if (Alive(heldWeapon)) Ammo = GetTutorialAmmo(heldWeapon!); else Ammo = 0;
        if (MemoryExperienced && !HasGun && !gunIntroduction && (player!.ActorLocation-TestWeapon.ActorLocation).Length()<850)
        {
            gunIntroduction = true;
            Host("Two choices. Take the amber pistol. The cyan one isn't worth your attention.");
        }
        LivingGuards = 0;
        foreach (var guard in guards)
        {
            if (!Alive(guard)) { if (!countedDeaths.Contains(guard)) WaveRewardEligible = false; continue; }
            if (GetTutorialGuardHealth(guard) > 0) { LivingGuards++; continue; }
            if (!countedDeaths.Add(guard)) continue;
            // The template unpossesses on death; retain ownership so detached controllers cannot leak.
            if (guardControllers.TryGetValue(guard, out var ai)) RetireController(ai);
            KilledGuards++;
            if (KilledGuards == requiredKills && WaveRewardEligible && !CardDropped)
            {
                AccessCard.SetActorLocation(guard.ActorLocation + new FVector(0,0,-35), false, out _, true);
                AccessCard.ActorHiddenInGame = false; CardDropped = true;
                Host(ChosenWeapon == 1
                    ? "Ten guards, and you're still standing! Now THAT is a performance. Your access card is well earned."
                    : "Nicely done. Pick up the access card. There's more to this room than gunfire.");
            }
        }
        if (RemoteActive && Alive(remoteTarget) && !GMOpen)
        {
            controller!.GetInputMouseDelta(out var x, out var y);
            PanTutorialCamera(x,y);
        }
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public void SetRegionFiring(bool firing)
    {
        if (!Alive(heldWeapon)) return;
        FireTutorialWeapon(heldWeapon!, firing && HasGun && Transition == 0 && !RemoteActive && !GMOpen && !PuzzleSubmitting && !VistaActive);
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public bool RegisterTutorialProjectile(AActor projectile, AActor shooter)
    {
        if (!Initialized || Transition != 0 || !Alive(projectile) || !Alive(shooter) || !(shooter == player || guards.Contains(shooter)))
        { RetireProjectile(projectile); return false; }
        regionProjectiles.Add(projectile);
        TrackPuzzleProjectile(projectile, shooter);
        return true;
    }

    private void EnterTutorialRemote(AActor camera, bool lesson)
    {
        if (RemoteActive || Transition != 0 || !Alive(camera)) return;
        SetRegionFiring(false);
        bodyRotation = controller!.ControlRotation;
        remoteTarget = camera; remoteEntryRotation = camera.ActorRotation;
        LessonTurned = false; remoteLesson = lesson; RemoteActive = true;
        LockInput(true); controller.SetViewTargetWithBlend(camera);
        if (CameraEnterSound is not null) UGameplayStatics.PlaySound2D(CameraEnterSound,.55f);
    }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public void PanTutorialCamera(float horizontal, float vertical)
    {
        if (!RemoteActive || !Alive(remoteTarget) || Transition != 0 || GMOpen) return;
        var r = remoteTarget!.ActorRotation;
        // UE MouseY is positive upwards, as in the already verified legacy camera.
        r.Yaw += horizontal*.25; r.Pitch = Math.Clamp(r.Pitch+vertical*.25,-50,35);
        remoteTarget.SetActorRotation(r,true);
        var yawDistance = Math.Abs(Math.IEEERemainder(r.Yaw-remoteEntryRotation.Yaw,360));
        LessonTurned |= yawDistance >= 10 || Math.Abs(r.Pitch-remoteEntryRotation.Pitch) >= 10;
    }

    private void CompleteRemoteLesson(bool normal)
    {
        if (!RemoteActive) return;
        if (normal && remoteLesson && LessonTurned && HasAccessCard && !CheckpointSaved && !CameraLearned)
        {
            ReportRegionProgress(AttemptId,2); SetTutorialGate(true);
            Host("Excellent. Follow the lights to the Signal Lab.");
            if (!CameraLessonNarrated)
            {
                CameraLessonNarrated=true;
                Say("A different point of view. That could be useful.");
            }
        }
        else if (normal && remoteLesson && !CameraLearned)
            Notice("Turn the training camera before returning.");
        remoteLesson = false;
        if (CameraExitSound is not null) UGameplayStatics.PlaySound2D(CameraExitSound,.45f);
    }

    private void SetTutorialGate(bool open)
    {
        if (!Alive(TutorialGate)) return;
        TutorialGate.ActorHiddenInGame=open; TutorialGate.ActorEnableCollision=!open;
    }

    private void ClearProjectiles()
    {
        puzzleShots.Clear();
        foreach (var a in regionProjectiles) RetireProjectile(a);
        regionProjectiles.Clear();
    }

    private void RetireProjectile(AActor projectile)
    {
        if (!Alive(projectile) || retiringProjectiles.Contains(projectile)) return;
        projectile.ActorHiddenInGame = true;
        projectile.ActorEnableCollision = false;
        foreach (var movement in projectile.GetComponentsByClass<UProjectileMovementComponent>())
            movement.StopMovementImmediately();
        foreach (var timeline in projectile.GetComponentsByClass<UTimelineComponent>()) timeline.Stop();
        retiringProjectiles.Add(projectile);
    }

    private void RestoreUnarmedPose()
    {
        foreach (var pose in unarmedPose)
            if (SystemLibrary.IsValid(pose.Mesh)) pose.Mesh.AnimInstanceClass = pose.AnimClass;
    }

    private void TrackGuard(AActor guard)
    {
        guards.Add(guard);
        if (guard is APawn pawn && Alive(pawn.Controller)) guardControllers[guard] = pawn.Controller;
        RegisterRegionTransient(guard,AttemptId);
    }

    private static void RetireController(AController ai)
    {
        if (!Alive(ai)) return;
        ai.UnPossess();
        // AController intentionally ignores K2_DestroyActor. Native lifespan expiry calls Destroy.
        ai.LifeSpan = .01f;
    }

    private void StopTutorialCombat()
    {
        SetRegionFiring(false); ClearProjectiles();
        foreach (var guard in guards) if (Alive(guard)) RemoveTutorialGuard(guard);
        foreach (var ai in guardControllers.Values) RetireController(ai);
        guardControllers.Clear();
        guards.Clear(); countedDeaths.Clear(); LivingGuards=0;
        HostText=""; hostRemaining=0;
    }

    private void ResetTutorial()
    {
        previousChoice = ChosenWeapon;
        ClearTutorialWeapon(player!); heldWeapon=null;
        RestoreUnarmedPose();
        ChosenWeapon=0; KilledGuards=0; CardDropped=false; requiredKills=0;
        WaveRewardEligible=false; gunIntroduction=false; LessonTurned=false;
    }

    private void RestoreSavedWeapon()
    {
        ClearTutorialWeapon(player!);
        RestoreUnarmedPose();
        heldWeapon=savedGun ? EquipTutorialWeapon(player!,savedChoice==1 ? 1 : 2) : null;
        ChosenWeapon=savedChoice;
    }

    private string RepeatThought() => PuzzleFailedBefore
        ? (puzzleEverObserved ? "The room reset, but I remember the real pattern. I still need my gun and access card."
            : "The wrong pattern killed me. I can skip the note, rearm, and check the camera this time.")
        : previousChoice==1
        ? "The amber pistol brought a crowd. Maybe I should choose the cyan one."
        : "I remember the note. I can skip it and go straight to the guns.";

    private void HandleTutorialGM(string key)
    {
        if (key == "Four")
        {
            if (!HasGun || CardDropped || HasAccessCard || CameraLearned || CheckpointSaved || guards.Count>=16)
            { Notice("GM: add guards during the teaching fight only (limit 16)."); return; }
            var guard=SpawnTutorialGuard(GuardSpawnPoints[guards.Count%GuardSpawnPoints.Count].ActorTransform);
            if (Alive(guard)) { TrackGuard(guard); requiredKills++; }
        }
        if (key == "Five")
        {
            var guard=guards.LastOrDefault(a=>Alive(a)&&GetTutorialGuardHealth(a)>0);
            if (guard is null) return;
            WaveRewardEligible=false; guards.Remove(guard); RemoveTutorialGuard(guard);
            Notice("GM removed a guard: no kill credit or card reward. Retry to restore the encounter.");
        }
        if (key == "Six" && Alive(TutorialCamera))
        { GMOpen=false; EnterTutorialRemote(TutorialCamera,HasAccessCard); }
        if (key == "Seven" && Alive(PuzzleCamera))
        { GMOpen=false; EnterTutorialRemote(PuzzleCamera,false); }
    }

    private void Host(string text, string guard = "")
    {
        HostText=text; hostRemaining=7;
        QueueDialogue(text,1,guard);
    }


    [UProperty(PropertyFlags.EditAnywhere)] public partial IList<AActor> PuzzleTiles { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor PuzzleCameraTarget { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor PuzzlePatternTarget { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor PuzzleSubmit { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor PuzzleClear { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor PuzzleArea { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial UMaterialInterface PuzzleOffMaterial { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial UMaterialInterface PuzzleOnMaterial { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial USoundBase PuzzleSuccessSound { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial USoundBase PuzzleFailureSound { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial int CorrectPatternMask { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial int BroadcastPatternMask { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool InPuzzleRoom { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool PatternObserved { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool PatternAligned { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool PuzzleFailedBefore { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool PuzzleSubmitting { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int PuzzleSubmitCount { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int PuzzleToggleCount { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string PuzzleStatus { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool PuzzleRemote { get; set; }
    private readonly Dictionary<AActor,(int Attempt,AActor Shooter)> puzzleShots = new(ReferenceEqualityComparer.Instance);
    private bool puzzleIntroduced, puzzleFailurePending, puzzleEverObserved;
    private float alignmentTime, puzzleResultTime;
    private bool PuzzleReady => Initialized && Transition == 0 && !CheckpointSaved && !PuzzleSolved
        && HasGun && HasAccessCard && CameraLearned && !PuzzleSubmitting;

    private void InitializePuzzle()
    {
        if (PuzzleTiles.Count != 9 || PuzzleTiles.Any(a=>!Alive(a)) || !Alive(PuzzleCamera)
            || !Alive(PuzzleCameraTarget) || !Alive(PuzzlePatternTarget) || !Alive(PuzzleSubmit)
            || !Alive(PuzzleClear) || !Alive(PuzzleArea) || PuzzleOffMaterial is null || PuzzleOnMaterial is null
            || CorrectPatternMask <= 0 || CorrectPatternMask > 511 || CorrectPatternMask == BroadcastPatternMask)
        { Initialized=false; FailureText="SIGNAL LAB SETUP INCOMPLETE - check assigned references."; return; }
        PuzzleStatus=""; RefreshPuzzleTiles();
    }

    private bool UpdatePuzzleFocus()
    {
        if (CheckpointSaved || PuzzleSubmitting) return false;
        if (Alive(PuzzleCamera) && Alive(PuzzleCameraTarget) && AimAt(PuzzleCameraTarget,2000,.998))
        { focused=PuzzleCamera; PromptText=HasAccessCard && CameraLearned ? "[E] Hack Signal Lab camera" : "Complete the training camera lesson first"; return true; }
        foreach (var a in new[]{PuzzleSubmit,PuzzleClear})
        {
            if (!Alive(a) || !AimAt(a,360,.985)) continue;
            focused=a;
            PromptText=PuzzleSolved ? "PATTERN ACCEPTED / Exit unlocked" : !PuzzleReady ? "Weapon and camera access required"
                : a==PuzzleSubmit ? "[E] Submit pattern / Wrong answer is lethal" : "[E] Clear all tiles / Safe";
            return true;
        }
        return false;
    }

    private bool InteractPuzzleFocus()
    {
        if (focused==PuzzleCamera)
        { if (HasAccessCard && CameraLearned && !PuzzleSubmitting) EnterTutorialRemote(PuzzleCamera,false); return true; }
        if (focused==PuzzleClear)
        { if (PuzzleReady) { PuzzleMask=0; RefreshPuzzleTiles(); Notice("PATTERN CLEARED",2); } return true; }
        if (focused!=PuzzleSubmit) return false;
        if (!PuzzleReady) return true;
        PuzzleSubmitCount++; SetRegionFiring(false); ClearProjectiles();
        if (PuzzleMask==CorrectPatternMask)
        {
            ReportRegionProgress(AttemptId,3); PuzzleStatus="PATTERN ACCEPTED / EXIT UNLOCKED"; puzzleResultTime=3;
            if (PuzzleSuccessSound is not null) UGameplayStatics.PlaySound2D(PuzzleSuccessSound,.65f);
            Host(PatternObserved ? "You found your own answer. Ignoring my instructions? Well played. The door is yours."
                : "Straight to the answer, without my reference? Confident. Well played. The door is yours.");
            Say("That memory beyond the door... I should recover it before going any further.",7);
        }
        else
        {
            PuzzleSubmitting=true; puzzleFailurePending=true; puzzleResultTime=1.4f;
            PuzzleStatus="PATTERN REJECTED / LETHAL RESET"; PuzzleFailedBefore=true;
            ClearDialogue(); Host("Wrong answer.");
            if (PuzzleFailureSound is not null) UGameplayStatics.PlaySound2D(PuzzleFailureSound,.65f);
            LockInput(true);
        }
        return true;
    }

    private void TickPuzzle(float delta)
    {
        if (!Initialized) return;
        PuzzleRemote=RemoteActive && remoteTarget==PuzzleCamera;
        if (Alive(PuzzleArea) && Alive(player))
        {
            PuzzleArea.GetActorBounds(false,out var center,out var extent,false);
            var q=player!.ActorLocation-center;
            InPuzzleRoom=Math.Abs(q.X)<=extent.X && Math.Abs(q.Y)<=extent.Y && Math.Abs(q.Z)<=extent.Z;
        }
        if (Transition!=0) return;
        if (PuzzleSolved && !string.IsNullOrEmpty(PuzzleStatus))
        {
            puzzleResultTime-=delta;
            if (puzzleResultTime<=0) PuzzleStatus="";
        }
        if (puzzleFailurePending)
        {
            puzzleResultTime-=delta;
            if (puzzleResultTime<=0) { puzzleFailurePending=false; ApplyRegionDamage(Health,AttemptId); }
            return;
        }
        if (PuzzleReady && InPuzzleRoom && !puzzleIntroduced)
        {
            puzzleIntroduced=true;
            Host("Copy the amber broadcast reference, then submit. A wrong answer is lethal.","unobserved");
            Say(PuzzleFailedBefore ? "His reference killed me. The camera might show a different answer."
                : "There is another camera here. Maybe I should look before I commit.",7,"unobserved");
        }
        PatternAligned=false;
        if (PuzzleRemote && Alive(PuzzlePatternTarget) && HasAccessCard && CameraLearned && !CheckpointSaved)
        {
            var direction=PuzzlePatternTarget.ActorLocation-PuzzleCamera.ActorLocation;
            var f=MathLibrary.GetForwardVector(PuzzleCamera.ActorRotation);
            var cosine=(direction.X*f.X+direction.Y*f.Y+direction.Z*f.Z)/direction.Length();
            PatternAligned=cosine>=Math.Cos(3*Math.PI/180);
            alignmentTime=PatternAligned ? alignmentTime+delta : 0;
            if (alignmentTime>=.7f && !PatternObserved)
            {
                PatternObserved=true; puzzleEverObserved=true;
                if (!PuzzleSolved)
                {
                    if (PuzzleMask==CorrectPatternMask)
                        Say("That matches what I've already entered. I can submit it now.",7,"ready-to-submit");
                    else
                        Say("An L, not the broadcast's T. I'll reproduce what this camera shows.",7,"needs-pattern");
                }
            }
        }
        else alignmentTime=0;
    }

    private void TrackPuzzleProjectile(AActor projectile,AActor shooter)
    {
        if (puzzleShots.ContainsKey(projectile)) return;
        puzzleShots[projectile]=(AttemptId,shooter);
        projectile.OnActorHit.Add(OnPuzzleProjectileHit);
        // Dead objects are removed here as well as on reset; no unbounded shot registry.
        foreach(var old in puzzleShots.Keys.Where(a=>!Alive(a)).ToArray()) puzzleShots.Remove(old);
    }

    [UFunction]
    public void OnPuzzleProjectileHit(AActor selfActor,AActor otherActor,FVector normalImpulse,FHitResult hit)
    {
        if (!puzzleShots.Remove(selfActor,out var shot) || shot.Attempt!=AttemptId || shot.Shooter!=player
            || !PuzzleReady || RemoteActive || GMOpen || !Alive(otherActor)) return;
        int index=PuzzleTiles.IndexOf(otherActor);
        if (index<0) return;
        PuzzleMask ^= 1<<index; PuzzleToggleCount++; RefreshPuzzleTiles();
        // Template wall-impact effects may hide the tile. Retire safely after the Hit stack finishes.
        RetireProjectile(selfActor);
    }

    private void RefreshPuzzleTiles()
    {
        for(int i=0;i<PuzzleTiles.Count;i++)
            if(Alive(PuzzleTiles[i]))
                foreach(var mesh in PuzzleTiles[i].GetComponentsByClass<UStaticMeshComponent>())
                    mesh.SetMaterial(0,(PuzzleMask&(1<<i))!=0 ? PuzzleOnMaterial : PuzzleOffMaterial);
    }

    private void CancelPuzzleAttempt()
    {
        puzzleFailurePending=false; PuzzleSubmitting=false; puzzleResultTime=0; alignmentTime=0;
        PatternAligned=false; PuzzleRemote=false; PuzzleStatus=""; puzzleShots.Clear();
    }

    private void ResetPuzzle()
    {
        CancelPuzzleAttempt(); PatternObserved=false; puzzleIntroduced=false; InPuzzleRoom=false;
        RefreshPuzzleTiles();
    }

    // Presentation owns no progression. Dialogue is scoped to the current attempt/objective.
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string SubtitleText { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int SubtitleSpeaker { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial float SubtitleRemaining { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int DialogueQueueCount { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial string NoticeText { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor VistaCamera { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor VistaTrigger { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor VistaStart { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor VistaEnd { get; set; }
    [UProperty(PropertyFlags.EditAnywhere)] public partial AActor VistaFocus { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool VistaActive { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial bool VistaPlayed { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial float VistaProgress { get; set; }
    [UProperty(PropertyFlags.BlueprintReadOnly)] public partial int VistaPlayCount { get; set; }
    private sealed record DialogueLine(string Text,int Speaker,string Scope,string Guard,int Attempt,float Duration);
    private readonly List<DialogueLine> dialogue = new();
    private DialogueLine? activeLine;
    private float dialogueGap,noticeRemaining,vistaTime;
    private int vistaPhase;
    private FRotator vistaBodyRotation;

    private string DialogueScope() => CheckpointSaved ? (VistaPlayed ? "vista" : "memory")
        : PuzzleSubmitting ? "rejected" : PuzzleSolved ? "solved"
        : CameraLearned ? (InPuzzleRoom ? "puzzle" : "travel")
        : HasAccessCard ? "camera" : CardDropped ? "card" : HasGun ? "fight"
        : MemoryExperienced ? "weapons" : "intro";

    private bool Relevant(DialogueLine line) => line.Attempt==AttemptId && line.Scope==DialogueScope()
        && (line.Guard!="unobserved" || !PatternObserved)
        && (line.Guard!="needs-pattern" || (!PuzzleSolved && PuzzleMask!=CorrectPatternMask))
        && (line.Guard!="ready-to-submit" || (!PuzzleSolved && PuzzleMask==CorrectPatternMask));

    private void QueueDialogue(string text,int speaker,string guard)
    {
        if (string.IsNullOrWhiteSpace(text) || Transition!=0) return;
        dialogue.RemoveAll(line=>!Relevant(line));
        // Sentence-sized cards, never two speakers at once. Ellipses remain part of a sentence.
        foreach(var sentence in System.Text.RegularExpressions.Regex.Split(text,@"(?<=[.!?])\s+(?=[A-Z])"))
        {
            var s=sentence.Trim(); if (s.Length==0) continue;
            if ((activeLine?.Text==s && Relevant(activeLine)) || dialogue.Any(line=>line.Text==s && line.Scope==DialogueScope())) continue;
            float duration=Math.Clamp(.8f+s.Split(' ',StringSplitOptions.RemoveEmptyEntries).Length/2.7f,2.5f,7);
            if (dialogue.Count>=12) dialogue.RemoveAt(0);
            dialogue.Add(new(s,speaker,DialogueScope(),guard,AttemptId,duration));
        }
        DialogueQueueCount=dialogue.Count;
    }

    private void TickNarrative(float delta)
    {
        noticeRemaining=Math.Max(0,noticeRemaining-delta);
        if(noticeRemaining==0) NoticeText="";
        if(!Initialized || Transition!=0) { ClearDialogue(); return; }
        dialogue.RemoveAll(line=>!Relevant(line));
        if(activeLine is not null && !Relevant(activeLine))
        { activeLine=null; SubtitleText=""; SubtitleSpeaker=0; SubtitleRemaining=0; dialogueGap=.15f; }
        if(activeLine is not null)
        {
            SubtitleRemaining=Math.Max(0,SubtitleRemaining-delta);
            if(SubtitleRemaining==0)
            { activeLine=null; SubtitleText=""; SubtitleSpeaker=0; dialogueGap=.3f; }
        }
        else
        {
            dialogueGap=Math.Max(0,dialogueGap-delta);
            if(dialogueGap==0 && dialogue.Count>0)
            {
                activeLine=dialogue[0];dialogue.RemoveAt(0);
                SubtitleText=activeLine.Text;SubtitleSpeaker=activeLine.Speaker;SubtitleRemaining=activeLine.Duration;
            }
        }
        DialogueQueueCount=dialogue.Count;
    }

    private void ClearDialogue()
    {
        dialogue.Clear();activeLine=null;SubtitleText="";SubtitleSpeaker=0;
        SubtitleRemaining=0;DialogueQueueCount=0;dialogueGap=0;
    }

    private void Notice(string text,float seconds=4)
    {
        NoticeText=text;noticeRemaining=seconds;
        ThoughtText=text;thoughtRemaining=seconds; // Backward-compatible GM diagnostics.
    }

    private void TickVista(float delta)
    {
        if (!Initialized || Transition!=0) return;
        if(!VistaActive)
        {
            if(!CheckpointSaved || VistaPlayed || RemoteActive || GMOpen || !Alive(VistaTrigger)) return;
            VistaTrigger.GetActorBounds(false,out var center,out var extent,false);
            var q=player!.ActorLocation-center;
            if(Math.Abs(q.X)>extent.X || Math.Abs(q.Y)>extent.Y || Math.Abs(q.Z)>extent.Z) return;
            if(!Alive(VistaCamera) || !Alive(VistaStart) || !Alive(VistaEnd) || !Alive(VistaFocus))
            { VistaPlayed=true;Notice("Overlook camera unavailable. Your checkpoint is safe.");return; }
            SetRegionFiring(false);ClearProjectiles();ClearDialogue();
            vistaBodyRotation=controller!.ControlRotation;VistaPlayed=true;VistaActive=true;VistaPlayCount++;
            vistaPhase=1;vistaTime=0;VistaProgress=0;GMOpen=false;
            VistaCamera.SetActorLocationAndRotation(VistaStart.ActorLocation,
                MathLibrary.FindLookAtRotation(VistaStart.ActorLocation,VistaFocus.ActorLocation),false,out _,true);
            LockInput(true);controller.SetViewTargetWithBlend(VistaCamera,.6f);
            Host("Welcome to the main arena.");
            Say("All this space... and every angle is watched.");
            return;
        }
        if(!Alive(VistaCamera) || !Alive(VistaStart) || !Alive(VistaEnd) || !Alive(VistaFocus))
        { FinishVista();ClearDialogue();Notice("View interrupted. Memory B is safe.");return; }
        vistaTime+=delta;
        if(vistaPhase==1)
        {
            float t=Math.Clamp(vistaTime/5,0,1);VistaProgress=t;
            double smooth=t*t*(3-2*t);
            var at=VistaStart.ActorLocation+(VistaEnd.ActorLocation-VistaStart.ActorLocation)*smooth;
            VistaCamera.SetActorLocationAndRotation(at,MathLibrary.FindLookAtRotation(at,VistaFocus.ActorLocation),false,out _,true);
            if(t>=1) { vistaPhase=2;vistaTime=0; }
        }
        else if(vistaPhase==2 && vistaTime>=2) ReturnFromVista(false);
        else if(vistaPhase==3 && vistaTime>=1) FinishVista();
    }

    private void ReturnFromVista(bool skipped)
    {
        if(!VistaActive || vistaPhase==3) return;
        if(skipped) ClearDialogue();
        vistaPhase=3;vistaTime=0;
        if(Alive(controller) && Alive(player))
        { controller!.ControlRotation=vistaBodyRotation;controller.SetViewTargetWithBlend(player!,1); }
    }

    private void FinishVista()
    {
        if(!VistaActive) return;
        VistaActive=false;vistaPhase=0;vistaTime=0;
        if(Alive(controller) && Alive(player))
        { controller!.SetViewTargetWithBlend(player!);controller.ControlRotation=vistaBodyRotation; }
        if(Transition==0) LockInput(false);
    }
}
