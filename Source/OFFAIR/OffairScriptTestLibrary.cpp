#include "OffairScriptTestLibrary.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

AActor* UOffairScriptTestLibrary::SpawnTestActor(const UObject* WorldContextObject, TSubclassOf<AActor> ActorClass)
{
    UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
    if (!World || World->WorldType != EWorldType::PIE || !ActorClass)
    {
        return nullptr;
    }

    FActorSpawnParameters Parameters;
    Parameters.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    return World->SpawnActor<AActor>(ActorClass, FVector::ZeroVector, FRotator::ZeroRotator, Parameters);
}
