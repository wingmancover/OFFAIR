#include "Modules/ModuleManager.h"

#if WITH_EDITOR && PLATFORM_WINDOWS
#include "Containers/Set.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY_STATIC(LogOffairEditorToolchain, Log, All);

namespace
{
void ConfigureEditorToolchain()
{
    FString SdkRoot = FPaths::ConvertRelativePathToFull(
        FPaths::Combine(FPaths::ProjectDir(), TEXT("Saved/Toolchains/Program Files/dotnet/")));
    FPaths::MakePlatformFilename(SdkRoot);
    if (!SdkRoot.EndsWith(TEXT("\\")))
    {
        SdkRoot += TEXT("\\");
    }
    if (!IFileManager::Get().FileExists(*(SdkRoot + TEXT("dotnet.exe"))))
    {
        UE_LOG(LogOffairEditorToolchain, Warning,
            TEXT("Project .NET SDK is missing. Run python Tools/unrealsharp.py setup before opening OFFAIR."));
        return;
    }

    // RunUAT.bat uses cmd.exe, which drops inherited variables over 8191 chars.
    // Preserve existing tool directories and order; remove only missing entries
    // and duplicates in this editor process. Never edit the OS/user PATH.
    TArray<FString> Entries;
    FPlatformMisc::GetEnvironmentVariable(TEXT("PATH")).ParseIntoArray(Entries, TEXT(";"), true);
    Entries.Insert(SdkRoot, 0);
    TArray<FString> ValidEntries;
    TSet<FString> Seen;
    for (FString Entry : Entries)
    {
        Entry.TrimStartAndEndInline();
        if (!FPaths::DirectoryExists(Entry))
        {
            continue;
        }
        FString Key = Entry;
        FPaths::NormalizeDirectoryName(Key);
        Key.ToLowerInline();
        if (!Seen.Contains(Key))
        {
            Seen.Add(Key);
            ValidEntries.Add(Entry);
        }
    }
    const FString ToolPath = FString::Join(ValidEntries, TEXT(";"));
    FPlatformMisc::SetEnvironmentVar(TEXT("PATH"), *ToolPath);
    FPlatformMisc::SetEnvironmentVar(TEXT("DOTNET_ROOT"), *SdkRoot);
    FPlatformMisc::SetEnvironmentVar(TEXT("UE_USE_SYSTEM_DOTNET"), TEXT("1"));
    FPlatformMisc::SetEnvironmentVar(TEXT("UE5Rules_DefineConstants"), TEXT("UE_5_8_OR_LATER"));
    UE_LOG(LogOffairEditorToolchain, Display, TEXT("Project SDK ready: %s; PATH length: %d"), *SdkRoot, ToolPath.Len());
}
}
#endif

class FOffairModule : public FDefaultGameModuleImpl
{
public:
    virtual void StartupModule() override
    {
        FDefaultGameModuleImpl::StartupModule();
#if WITH_EDITOR && PLATFORM_WINDOWS
        ConfigureEditorToolchain();
#endif
    }
};

IMPLEMENT_PRIMARY_GAME_MODULE(FOffairModule, OFFAIR, "OFFAIR");
